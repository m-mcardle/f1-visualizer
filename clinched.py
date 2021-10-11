mostPoints = {
    '2019': '26',
    '2010': '25',
    '1991': '10',
    '1961': '9',
    '1960': '8',
    '1950': '9'
}

mostPointsConstructors = {
    '2019': '44',
    '2010': '43',
    '2003': '18',
    '1991': '16',
    '1962': '15',
    '1950': '14'
}


def calculateClinch(year, racesLeft, pointsFromLeader, drivers=True):
    mostPointsThisYear = 26

    if drivers:
        pointsList = mostPoints
    else:
        pointsList = mostPointsConstructors

    for key in pointsList:
        if int(key) <= int(year):
            mostPointsThisYear = pointsList[key]
            break

    pointsAvailable = float(mostPointsThisYear) * float(racesLeft)

    if float(pointsFromLeader) > float(pointsAvailable):
        return False
    else:
        return True

