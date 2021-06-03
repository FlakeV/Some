import time
import re
import logging
import os
import pika
import json

from flask import current_app as app
from sqlalchemy import func

from datetime import datetime, timedelta
from ..model_schema import PlotsUploadSession, PlotsUploadSessionSchema, DraftPlot


class CustomerService():
    def sendOnboardedPlotsMsgToProcessingQueue(self, customer_id, plots):
        plotIds = []
        for plot in plots:
            plotIds.append(str(plot.id))
        newPlotsMsg = {
            "event_type": "PlotsOnboarded",
            "data": {
                "customer_id": customer_id,
                "plot_ids": plotIds
            }
        }
        connection = None
        try:
            # create connection
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=app.config['CS_RABBIT_ADDR']))
            channel = connection.channel()
            channel.exchange_declare(exchange=app.config['CS_RABBIT_EXCHANGE'], exchange_type='fanout', durable=True)
            # send message
            channel.basic_publish(exchange=app.config['CS_RABBIT_EXCHANGE'], routing_key=app.config['CS_RABBIT_QUEUE'], body=json.dumps(newPlotsMsg))
            app.logger.info("New plots onboarded message published in RabbitMQ")
            connection.close()
        except Exception as e:
            app.logger.error(e)
            app.logger.error("New plots failed to be pushed to processing queue in RabbitMQ")
            if connection:
                connection.close()
        return

    def createPLotsUploadSession(self, uploadRecordObj, customer_id, dbSession):
        uploadSessionSearchQuery = dbSession.query(PlotsUploadSession).filter(PlotsUploadSession.customer_id == customer_id)
        uploadSessionSearchQuery = uploadSessionSearchQuery.filter(PlotsUploadSession.plots_setup_stage != Constants.DRAFT_SESSION_STATUS_COMPLITED)
        uploadSessionSearchQuery = uploadSessionSearchQuery.filter(PlotsUploadSession.plots_setup_stage != Constants.DRAFT_SESSION_STATUS_ABADONED)
        if uploadSessionSearchQuery.first():
            for session in uploadSessionSearchQuery:
                session.plots_setup_stage = Constants.DRAFT_SESSION_STATUS_ABADONED
                dbSession.add(session)
        dbSession.add(uploadRecordObj)
        return uploadRecordObj

    def savePlotsDraft(self, plotsObjectArray, customerId, uploadPlotSessionID, dbSession):
        savedPlotsArray = []
        for plot in plotsObjectArray:
            areaRow = dbSession.query(func.ST_Area(
                func.ST_Transform(plot.geometry, Constants.CRS_METRIC_SYSTEM)
            )).first()
            plot.area = areaRow[0]
            plot.plots_upload_session_id = uploadPlotSessionID
            plot.customer_id = customerId
            plot.status = Constants.STATUS_ACTIVE
            savedPlotsArray.append(plot)
        dbSession.add_all(savedPlotsArray)
        return savedPlotsArray

    def saveDraftAttributMmapping(self, attributeMappingJSON, uploadPlotSessionID, dbSession):
        uploadPlotSessionSearch = dbSession.query(PlotsUploadSession).filter(PlotsUploadSession.id == uploadPlotSessionID)
        uploadPlotSessionSearch = dbSession.filter(PlotsUploadSession.plots_setup_stage != Constants.DRAFT_SESSION_STATUS_ABADONED)
        uploadPlotSession = uploadPlotSessionSearch.first()
        if uploadPlotSession:
            uploadPlotSession.plots_setup_stage = Constants.DRAFT_SESSION_STATUS_PLOTS_SAVED
            uploadPlotSession.attribute_mapping_json = attributeMappingJSON
            dbSession.add(uploadPlotSession)
            return uploadPlotSession
        else:
            return False

    def updateDrafts(self, plotsObjectArray, uploadPlotSessionID, dbSession):
        updatedPlotsArray = []
        draftsSearchQuery = dbSession.query(DraftPlot).filter(DraftPlot.plots_upload_session_id == uploadPlotSessionID)
        for draftPlot in draftsSearchQuery:
            for newDraft in plotsObjectArray:
                if draftPlot.id == newDraft.id:
                    draftPlot = newDraft
                    updatedPlotsArray.append(draftPlot)
        dbSession.add_all(updatedPlotsArray)
        return updatedPlotsArray

    def getLastDrafts(self, customerId, dbSession):
        # get attribute mapping
        uploadSessionSearchQuery = dbSession.query(PlotsUploadSession)
        uploadSessionSearchQuery = uploadSessionSearchQuery.filter(PlotsUploadSession.plots_setup_stage != Constants.DRAFT_SESSION_STATUS_ABADONED)
        uploadSessionSearchQuery = uploadSessionSearchQuery.order_by(PlotsUploadSession.updated_at.desc())
        sessionUpload = uploadSessionSearchQuery.first()
        if sessionUpload:
            sessionUploadId = sessionUpload.id
            draftsSearchQuery = dbSession.query(DraftPlot).filter(DraftPlot.upload_session_id == sessionUploadId)
            drafts = draftsSearchQuery.all()
            return sessionUpload, drafts
        else:
            return False, False

    def singleDraftUpdate(self, draft, customerId, dbSession):
        areaRow = dbSession.query(func.ST_Area(
            func.ST_Transform(draft.geometry, Constants.CRS_METRIC_SYSTEM)
        )).first()
        draft.area = areaRow[0]
        draft.customer_id = customerId
        draft.status = Constants.STATUS_ACTIVE
        dbSession.add(draft)
        return draft

    def getDraft(self, customer_id, sessionUploadId, draftId, dbSession):
        draftSearchQuery = dbSession.query(DraftPlot).filter(DraftPlot.customer_id == customer_id, DraftPlot.plots_upload_session_id == sessionUploadId)
        draftSearchQuery = draftSearchQuery.filter(DraftPlot.id == draftId)
        return draftSearchQuery.first()

    def addSingleDraft(self, draft, dbSession):
        dbSession.add(draft)
        return draft

    def getDraftsForFinalasing(self, sessionUploadId, dbSession):
        draftsSearchQuery = dbSession.query(DraftPlot).filter(DraftPlot.upload_session_id == sessionUploadId)
        draftsObj = draftsSearchQuery.all()
        uploadSessionSearchQuery = dbSession.query(PlotsUploadSession).filter(PlotsUploadSession.id == sessionUploadId)
        uploadSession = uploadSessionSearchQuery.first()
        if uploadSession.plots_setup_stage == Constants.DRAFT_SESSION_STATUS_ABADONED:
            return False
        else:
            uploadSession.plots_setup_stage = Constants.DRAFT_SESSION_STATUS_COMPLITED
            dbSession.add(uploadSession)
        return draftsObj

    def clearSessionId(self, draftsJson):
        for draft in draftsJson:
            draft.pop('upload_session_id', None)
        return draftsJson