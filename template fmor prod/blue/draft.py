import os
import uuid
import pathlib
import geopandas as gpd
import pandas as pd
import json
import shapely

from requests import HTTPError
from flask import Flask, request, jsonify, Blueprint, current_app, abort, redirect, url_for
from flask import current_app as app
from werkzeug.utils import secure_filename
from shapely import geometry
from shapely.geometry import box, Polygon, MultiPolygon, shape, Point
from sqlalchemy import func
from geoalchemy2.elements import WKTElement
from datetime import datetime

from ..util import Constants
from ..model_schema import Plot, PlotSchema, Customer, CustomerSchema, FileUploadRecord, PlotSearchParams, Measurement, MeasurementSchema, PlotsUploadSession, DraftPlotSchema
from ..services import CustomerService


@bp.route('/<customer_id>/file-upload/', methods=['POST'])
def draft_file_upload(customer_id):
    # check if the post request has the file part
    if 'plots_file' not in request.files:
        return jsonify({"status": "error", "description": "No file found as input"}), 400
    uploadedFile = request.files['plots_file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if uploadedFile.filename == '':
        return jsonify({"status": "error", "description": "No file found as input"}), 400
    # check if uploaded file is ain allowed file types
    if uploadedFile and allowed_file(uploadedFile.filename):
        origFileName = uploadedFile.filename
        fileType = uploadedFile.filename.rsplit('.', 1)[1].lower()
        filename = str(uuid.uuid4()) + "." + fileType
        today = datetime.now()
        dateBasedDir = today.strftime('%Y{0}%m{0}%d').format(os.path.sep)
        uploadFolder = os.path.join(app.config['PLOT_FILE_UPLOAD_FOLDER'], dateBasedDir, customer_id)
        # create folders if not already existing
        os.makedirs(uploadFolder, exist_ok=True)
        fileURI = os.path.join(uploadFolder, filename)
        uploadedFile.save(fileURI)
        # process uploaded file
        plotsArray = app.geospatial_service.processUploadedFileForPlots(fileURI, fileType, customer_id)
        plotsSchema = PlotSchema(many=True)
        plotsJson = plotsSchema.dump(plotsArray)
        # create a db session
        Session = app.session
        dbSession = Session()
        # Record upload history
        uploadRecord = FileUploadRecord()
        uploadRecord.file_name_orig = origFileName
        uploadRecord.file_name_uuid = filename
        uploadRecord.file_type = fileType
        uploadRecord.file_path = fileURI
        uploadRecord.upload_context = Constants.UPLOAD_CONTEXT_PLOTS
        uploadRecord.status = Constants.STATUS_ACTIVE
        uploadRecord.customer_id = customer_id
        uploadRecord = app.customer_service.createFileUploadRecord(uploadRecord, dbSession)
        dbSession.commit()
        uploadRecordId = uploadRecord.id
        # create upload session
        uploadPlotSession = PlotsUploadSession()
        uploadPlotSession.file_upload_record_id = uploadRecordId
        uploadPlotSession.customer_id = customer_id
        uploadPlotSession.plots_setup_stage = Constants.DRAFT_SESSION_STATUS_FILE_UPLOADED
        dbSession.commit()
        uploadPlotSessionID = uploadPlotSession.id
        dbSession.close()
        # save draft
        savedDrafts = app.customer_service.savePlotsDraft(plotsArray, customer_id, uploadPlotSessionID, dbSession)
        plotsJson = DraftPlotSchema.dump(savedDrafts)
        # return json results
        return jsonify({
            "status": "success",
            "description": "Plot file successfully processed",
            "fileUploadRef": uploadRecordId,
            "plot_uploads_session_id": uploadPlotSessionID,
            "plots": plotsJson
        }), 200
    return


@bp.route('/<customer_id>/<upload_session_id>/save-plots-draft/', methods=['PUT'])
def savePlotsDraft(customer_id, upload_session_id):
    updateJson = request.json
    plotsJson = updateJson["plots"]
    attributeMappingJson = updateJson["attribute_mapping"]
    Session = app.session
    dbSession = Session()
    # add draft plot
    draftPlotsSchema = DraftPlotSchema(many=True)
    customerService = app.customer_service
    isValid = customerService.validateSchema(draftPlotsSchema, plotsJson, dbSession)
    try:
        if isValid:
            plots = draftPlotsSchema.load(plotsJson, session=dbSession)
            savedDrafts, updatedDrafts = customerService.updatedDrafts(plots, upload_session_id, dbSession)
            dbSession.commit()
        else:
            dbSession.rollback()
            dbSession.close()
            return jsonify({
                "status": "error",
                "description": "Plots json not valid"
            }), 400
        # save attribute_mapping
        session = customerService.saveDraftAttributMmapping(attributeMappingJson, upload_session_id, dbSession)
        if session:
            dbSession.commit()
            dbSession.close()
            return jsonify({
                "status": "succes",
                "description": "draft saving complete successfully",
                "draft_updated": updatedDrafts
            }), 200
        else:
            dbSession.rollback()
            dbSession.close()
            return jsonify({
                "status": "error",
                "description": "active draft upload session not found"
            }), 400
    except Exception as e:
        dbSession.rollback()
        dbSession.close()
        app.logger.error(e)
        return jsonify({
            "status": "error",
            "description": "draft save failed"
        }), 500


@bp.route('<customer_id>/last-upload-session-data/', methods=['GET'])
def getDetailsLastUploadDraftSession(customer_id):
    Session = app.session
    dbSession = Session()
    sessionUpload, drafts = app.customer_service.getLastDrafts(customer_id, dbSession)
    if sessionUpload:
        draftsJson = DraftPlotSchema.dupm(drafts)
        dbSession.close()
        return jsonify({
            "status": "succes",
            "description": "last upload session found",
            "upload_session_id": sessionUpload.id,
            "plots": draftsJson,
            "attribute_mapping": sessionUpload.attribute_mapping
        }), 200
    else:
        jsonify({
            "status": "error",
            "description": "last upload session not found"
        }), 400


@bp.route('<customer_id>/plot-draft/<upload_session_id>/<draft_plot_id>/', methods=['PUT'])
def singleDraftUpdate(customer_id, upload_session_id, draft_plot_id):
    if request.method == 'PUT' and request.get_json(force=True):
        draftJson = request.json
    # create a db session
    Session = app.session
    dbSession = Session()
    draftSchema = DraftPlotSchema()
    customerService = app.customer_service
    isValid = customerService.validateSchema(draftSchema, draftJson, dbSession)
    try:
        if isValid:
            origDraft = customerService.getDraft(customer_id, upload_session_id, draft_plot_id, dbSession)
            newDraft = draftSchema.load(draftJson, instance=origDraft, session=dbSession)
            savedDraft = customerService.singleDraftUpdate(newDraft, customer_id, dbSession)
            dbSession.commit()
            plotsSavedJsonDump = draftJson.dump(savedDraft)
            dbSession.close()
            return jsonify({
                "status": "success",
                "description": "Process completed successfully",
                "plot_saved": plotsSavedJsonDump
            }), 200
        else:
            dbSession.rollback()
            dbSession.close()
            return jsonify({
                "status": "error",
                "description": "Draft json not valid"
            }), 400
    except Exception as e:
        dbSession.rollback()
        dbSession.close()
        app.logger.error(e)
        return jsonify({
            "status": "error",
            "description": "Draft save failed"
        }), 500


@bp.route('/<customer_id>/plots/setup/<plot_upload_session_id>/plot-draft/', methods=["POST"])
def addSingleDraftInUploadSession(customer_id, plot_upload_session_id):
    if request.method == 'POST' and request.get_json(force=True):
        draftJson = request.json
        draftJson['plots_upload_session_id'] = plot_upload_session_id
    Session = app.session
    dbSession = Session()
    draftSchema = DraftPlotSchema()
    customerService = app.customer_service
    isValid = customerService.validateSchema(draftSchema, draftJson, dbSession)
    try:
        if isValid:
            draft = draftSchema.load(draftJson, session=dbSession)
            savedDraft = customerService.singleDraftUpdate(draft, dbSession)
            return jsonify({
                "status": "success",
                "description": "Process completed successfully",
                "plot_saved": savedDraft
            })
        else:
            dbSession.rollback()
            dbSession.close()
            return jsonify({
                "status": "error",
                "description": "Draft json not valid"
            }), 400
    except Exception as e:
        dbSession.rollback()
        dbSession.close()
        app.logger.error(e)
        return jsonify({
            "status": "error",
            "description": "Draft save failed"
        }), 500


@bp.route('/<customer_id>/plots/setup/<upload_session_id>/finalise-draft/', methods=["POST"])
def finaliseDraft(customer_id, upload_session_id):
    Session = app.session
    dbSession = Session()
    customerService = app.customer_service
    drafts = customerService.getDraftsForFinalasing(upload_session_id, dbSession)
    if drafts:
        plotsSchema = PlotSchema(many=True)
        plotsJson = customerService.clearSessionId(drafts)
        isValid = customerService.validateSchema(plotsSchema, plotsJson, dbSession)
        try:
            if isValid:
                plots = plotsSchema.load(plotsJson, session=dbSession)
                savedPlots, skippedPlots = customerService.savePlots(plots, customer_id, dbSession)
                dbSession.commit()
                # send plots to processing queue
                customerService.sendOnboardedPlotsMsgToProcessingQueue(customer_id, savedPlots)
                plotsSavedJsonDump = plotsSchema.dump(savedPlots)
                plotsSkippedJsonDump = plotsSchema.dump(skippedPlots)
                dbSession.close()
                return jsonify({
                    "status": "success",
                    "description": "Process completed successfully",
                    "plots_saved": plotsSavedJsonDump,
                    "plots_skipped": plotsSkippedJsonDump
                }), 200
            else:
                dbSession.rollback()
                dbSession.close()
                return jsonify({
                    "status": "error",
                    "description": "Plots json not valid"
                }), 400
        except Exception as e:
            dbSession.rollback()
            dbSession.close()
            app.logger.error(e)
            return jsonify({
                "status": "error",
                "description": "Plot save failed"
            }), 500
    else:
        dbSession.rollback()
        dbSession.close()
        return jsonify({
            "status": "error",
            "description": "Active upload session not found"
        }), 400

