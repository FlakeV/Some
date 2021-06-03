import sys
import datetime
 
#type = sys.stdin.readline().strip()
#dates = sys.stdin.readline().strip()

type = input().strip()
dates = input().strip()
countTimes = 0
arrayTimes = []
datesStart, datesEnd =  dates.split(' ')
startYear, startMounth, startDay = datesStart.split('-')
endYear, endMounth, endDay = datesEnd.split('-')
start = datetime.date(int(startYear), int(startMounth), int(startDay))
end = datetime.date(int(endYear), int(endMounth), int(endDay))

if type == 'WEEK':  
    weekDay = start.isoweekday()
    startTime = start
    endTime = start + datetime.timedelta(days=(7-weekDay))
    while endTime < end:
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(endTime))
        startTime = endTime + datetime.timedelta(days=1)
        endTime = startTime + datetime.timedelta(days=6)
    else:    
        endTime = end
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(endTime))

elif type == 'MONTH':
    nextMounth = datetime.date(int(startYear), int(startMounth) + 1, 1)
    startTime = start
    while nextMounth < end:
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextMounth - datetime.timedelta(days=1)))
        startTime = nextMounth
        nextMounth = datetime.date(int(startTime.year), int(startTime.month) + 1, 1)
    else:    
        nextMounth = end
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextMounth))

elif type == 'QUARTER':
    startTime = start
    nextQUARTER = datetime.date(int(startYear), int(startMounth) + (int(startMounth)), 1)
    while nextQUARTER < end:
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextQUARTER - datetime.timedelta(days=1)))
        startTime = nextQUARTER
        if int(startTime.month) + 3 > 12:
            nextQUARTER = datetime.date(int(startTime.year) + 1, int(startTime.month) + 3 - 12, 1)
        else:
            nextQUARTER = datetime.date(int(startTime.year), int(startTime.month) + 3, 1)
    else:    
        nextQUARTER = end
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextQUARTER))

elif type == 'YEAR':
    startTime = start
    nextYear = datetime.date(int(startYear) + 1, 1, 1)
    while nextYear < end:
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextYear - datetime.timedelta(days=1)))
        startTime = nextYear
        nextYear = datetime.date(int(startTime.year) + 1, 1, 1)
    else:    
        nextYear = end
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextYear))

elif type == 'REVIEW':
    startTime = start
    if  startTime > datetime.date(int(startYear), 9, 30):
        nextREVIEW = datetime.date(int(startTime.year) + 1, 4, 1)
    else:
        nextREVIEW = datetime.date(int(startTime.year), 10, 1)
    while nextREVIEW < end:
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextREVIEW + datetime.timedelta(days=1)))
        startTime = nextREVIEW
        if  startTime > datetime.date(int(startTime.year), 9, 30):
            nextREVIEW = datetime.date(int(startTime.year) + 1, 4, 1)
        else:
            nextREVIEW = datetime.date(int(startTime.year), 10, 1)
    else:    
        nextREVIEW = end
        countTimes +=1
        arrayTimes.append(str(startTime) + ' ' + str(nextREVIEW))

print(countTimes)
for time in arrayTimes:
    print(time)
