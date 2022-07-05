# import pycurl
import requests
import xml.etree.ElementTree as ET
import time
import dash
import plotly.express as px
import pandas as pd
import sys
import logging
import logging.handlers
from dash import dcc
from dash import html
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output
from requests.api import get
import random
from clinched import calculateClinch
import threading
import requests_cache
from ratelimit import limits, RateLimitException, sleep_and_retry

print(dash.__version__)
print(requests.__version__)
print(pd.__version__)
exit()


urls_expire_after = {
    '*/last/*': 604800
}
requests_cache.install_cache('request_cache', urls_expire_after=urls_expire_after)


pd.options.plotting.backend = "plotly"

app = dash.Dash(__name__)

evt = threading.Event()
evt.set()

ns = "{http://ergast.com/mrd/1.5}"

# Dictionary containing keys of drivers name, and values of Lists containing total points after each race
standings = dict()

# Array containing colours to use for each driver
standingsTeamColours = []

# Array containing marks that indicate if they are still in contention
standingsEliminated = []

teamColours = {
    "Alfa Romeo": "maroon",
    "AlphaTauri": "grey",
    "Alpine F1 Team": "blue",
    "Aston Martin": "green",
    "Red Bull": "navy",
    "Brawn": "chartreuse",
    "BAR": "whitesmoke",
    "BMW Sauber": "cornflowerblue",
    "BRM": "darkgreen",
    "Benetton": "skyblue",
    "Brabham": "darkblue",
    "Brabham-Repco": "green",
    "Caterham": "green",
    "Cooper-Castellotti": "green",
    "Cooper-Climax": "midnightblue",
    "Cooper-Maserati": "red",
    "Dallara": "red",
    "Epperly": "yellow",
    "Euro Brun": "orange",
    "Fittipaldi": "yellow",
    "Footwork": "whitesmoke",
    "Forti": "yellow",
    "Force India": "coral",
    "Ferrari": "red",
    "HRT": "whitesmoke",
    "Haas F1 Team": "whitesmoke",
    "Honda": "whitesmoke",
    "Jaguar": "green",
    "Jordan": "limegreen",
    "Larrousse": "navy",
    "Leyton House": "lightskyblue",
    "Ligier": "blue",
    "Lotus": "black",
    "Lotus F1": "black",
    "MF1": "red",
    "Manor Marussia": "orange",
    "Marussia": "red",
    "Maserati": "darkred",
    "McLaren": "orange",
    "McLaren-Alfa Romeo": "yellow",
    "McLaren-Ford": "whitesmoke",
    "Mercedes": "aqua",
    "Minardi": "yellow",
    "Renault": "yellow",
    "Racing Point": "hotpink",
    "Sauber": "crimson",
    "Spyker": "orange",
    "Spyker MF1": "orange",
    "Super Aguri": "whitesmoke",
    "Team Lotus": "green",
    "Toro Rosso": "midnightblue",
    "Toleman": "blue",
    "Toyota": "whitesmoke",
    "Tyrrell": "mediumblue",
    "Williams": "lightblue",
    "Virgin": "orange",
    "Gold": "gold",
    "Silver": "silver",
}
# Use this to build out list of colours


totalRaces = 100 # Integer for total amount of races scheduled in a season
maxRace = 100 # Integer for amount of races completed in a season
driverStandings = True # Boolean for if driver standings should be displayed

raceNames = dict() # Dictionary containing the html values to include for each mark label for the slider

years = [*range(1950, 2023, 1)] # Range of years that this program supports

# Variables that contain the year that the standings have been loaded for and amount of races the dictionary has been filled out for
loadedYear = 0
loadedRaces = 0

# Set up the logging
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

# Build our log handler with formatting
fileHandler = logging.FileHandler('f1-visualizer.log')
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

if len(sys.argv) <= 1:
    level = "ERROR"
elif sys.argv[1].upper() == "DEBUG":
    level = "DEBUG"
elif sys.argv[1].upper() == "ERROR":
    level = "ERROR"
elif sys.argv[1].upper() == "WARNING":
    level = "WARNING"
elif sys.argv[1].upper() == "INFO":
    level = "INFO"
else:
    level = "ERROR"


rootLogger.setLevel(level=level)

app.layout = html.Div([
    html.Div(
        dcc.Graph(
            id='f1-graph',
        )
    ),
    html.Div([
        html.Div([
            html.Div([
                dcc.Slider(
                    id='f1-slider',
                    min=1,
                    max=maxRace,
                    value=1,
                    step=1,
                    dots=True
                ),
                ], style={'width': '50%', 'display': 'inline-block'}
            ),
            dcc.Dropdown(
                id='f1-year',
                options=[{'label': str(i), 'value': str(i)} for i in years],
                value='2022',
                style={'width': '50%', 'display': 'inline-block'}
            ),
            ], style={'text-align': 'center'}
        ),
        html.Div([
            html.Button("Previous Race", id="previousRace", style={'margin': 'auto', 'padding': '10px', 'width': '30%'}),
            html.Button("Next Race", id="nextRace", style={'margin': 'auto', 'padding': '10px', 'width': '30%'})
            ], style={'text-align': 'center', 'margin': 'auto', 'padding': '10px', 'width': '50%'}
        ),
        html.Div([
            html.Button("View Constructors Standings", id="standingsToggle", style={'margin': 'auto', 'padding': '10px', 'width': '30%'})
            ], style={'text-align': 'center', 'margin': 'auto', 'padding': '10px', 'width': '50%'}
        )
    ])
])


# Rate-limiting Requests
TWO_MINUTES = 120
MAX_CALLS = 6

@sleep_and_retry
@limits(calls=MAX_CALLS, period=TWO_MINUTES)
def make_request(req):
    rootLogger.info(req)
    resp = requests.get(req)
    return (resp)


# Summary: Function to clear all lists and reset loadedRaces to 0
def clearStandings():
    global loadedRaces
    standings.clear()
    standingsTeamColours.clear()
    standingsEliminated.clear()
    loadedRaces = 0


def getStandingsType():
    global driverStandings
    if driverStandings:
        return "driverStandings"
    else:
        return "constructorStandings"

def getLeaderPoints():
    leaderPoints = -1
    leaderName = "None"
    for key in standings:
        if standings[key][loadedRaces] > leaderPoints:
            leaderPoints = standings[key][loadedRaces]
            leaderName = key

    return { 'name': leaderName, 'points': leaderPoints }

# Summary: Function that will call on calculateClinch and build out an array 
# of data points that indicates drivers/teams eliminated from contention
def checkForClinch():
    leader = getLeaderPoints()
    leaderPoints = leader['points']
    leaderName = leader['name']
    racesLeft = int(totalRaces) - int(loadedRaces)

    i = 0
    for name in standings:
        points = standings[name][loadedRaces]
        pointsFromLeader = float(leaderPoints) - float(points)
        if name == leaderName or calculateClinch(loadedYear, racesLeft, pointsFromLeader, driverStandings):
            rootLogger.debug(f"{name} still in contention. Only {pointsFromLeader} back of 1st with {racesLeft} races left. Has {points} points")
        else:
            rootLogger.debug(f"{name} NOT in contention. Is {pointsFromLeader} back of 1st with only {racesLeft} races left. Has {points} points")

            standingsEliminated.append({'x': loadedRaces, 'y': points})
        i += 1

# Summary: Initializes the drivers standing by adding an element into each driver's array for each race
# 
# param race: Integer representing the amount of races to initialize up to (ex: race = 2 ==> [0, 0, 0])
# param year: Integer representing the year that will be parsed, if the year is changed then reset loadedRaces
def FillDriversStandings(race, year):
    global loadedRaces
    global loadedYear
    global maxRace
    global standingsTeamColours

    if race > maxRace:
        race = maxRace

    if year != loadedYear:
        rootLogger.info("Year has changed, clearing standings.")
        clearStandings()
        loadedYear = year

    diff = int(loadedRaces) - int(race) # TODO: bug where race = 'None' :P
    if diff > 0:
        rootLogger.info('Clearing %s races', str(diff))
        for driver in standings:
            for i in range(0, diff):
                del standings[driver][-1] # must have an item in it
        i = 0
        standingsEliminatedCopy = standingsEliminated.copy()
        for xy in standingsEliminatedCopy: # Delete all annotations that are now in races that aren't loaded
            if xy['x'] > race:
                del standingsEliminated[i]
            else:
                i += 1
        
        loadedRaces = race

    standingsType = getStandingsType()

    if loadedRaces < 1: # If no races are loaded, then get the list of drivers to init as a request
        # with requests_cache.disabled():
        response = make_request(f'http://ergast.com/api/f1/{year}/last/{standingsType}')
        content = response.text
        root = ET.fromstring(content)
        lastRace = root.find(f".//{ns}StandingsTable")

        maxRace = int(lastRace.attrib["round"])

        if standingsType == "driverStandings":
            allDriverRankings = lastRace.findall(f".//{ns}DriverStanding")
            for driver in allDriverRankings:
                # TODO maybe this isn't the best, what if driver of same name
                firstName = driver.find(f".//{ns}GivenName").text
                lastName = driver.find(f".//{ns}FamilyName").text
                fullName = firstName + " " + lastName

                team = driver.find(f".//{ns}Constructor/{ns}Name").text

                for i in range(loadedRaces, race):
                    if fullName not in standings:
                        standings[fullName] = [0.0, 0.0]
                        if team in teamColours:
                            standingsTeamColours.append(teamColours[team])
                        else:
                            standingsTeamColours.append(random.choice(list(teamColours.values())))
                    else:
                        standings[fullName].append(0.0)
        else:
            allTeams = lastRace.findall(f".//{ns}Constructor")
            for team in allTeams:
                name = team.find(f".//{ns}Name").text

                for i in range(loadedRaces, race):
                    if name not in standings:
                        standings[name] = [0.0, 0.0]
                        if name in teamColours:
                            standingsTeamColours.append(teamColours[name])
                        else:
                            standingsTeamColours.append(random.choice(list(teamColours.values())))
                    else:
                        standings[name].append(0.0)
    else: # If the driverStandings is already initialized then just add a new element for each new race
        for element in standings:
            for i in range(loadedRaces, race):
                standings[element].append(0.0)

    return True
    

# Summary: Builds the drivers standing by looping for each standings after race amount of races
# 
# param race: Integer representing the amount of races to parse for
# param year: Integer representing the year to parse for
def StandingsBuilder(race, year):
    global loadedRaces
    global loadedYear
    global maxRace 
    global driverStandings

    if race > maxRace + 1:
        race = maxRace + 1
    
    standingsType = getStandingsType()

    rootLogger.info('Building Standings after %s races in %s', race, year)

    for currentRace in range(loadedRaces + 1, race + 1):

        rootLogger.info('Sending Request for Race %s', str(currentRace))

        response = make_request(f'http://ergast.com/api/f1/{year}/{currentRace}/{standingsType}')
        rootLogger.info("Received Response")

        content = response.text
        # print(content)


        root = ET.fromstring(content)

        results = root.findall(f".//{ns}StandingsList/*")

        rootLogger.info("Parsing Start")
        for result in results:
            points = result.attrib["points"]

            if standingsType == "driverStandings":
                firstName = result.find(f"./{ns}Driver/{ns}GivenName")
                lastName = result.find(f"./{ns}Driver/{ns}FamilyName")

                name = f"{firstName.text} {lastName.text}"
                rootLogger.debug("Driver: %s", name)
            else:
                name = result.find(f"./{ns}Constructor/{ns}Name").text
                rootLogger.debug("Constructor: %s", name)

            if name not in standings: # If driver not initialized in standings then skip him
                continue

            standings[name][currentRace] = (float(points)) # TODO bug index out of range using previous twice then next once



        rootLogger.info("Parsing End")
        loadedRaces = currentRace
        checkForClinch()

    loadedRaces = race

    rootLogger.info(f"Loaded Races = {loadedRaces}. Loaded Year = {loadedYear}\n")
    

# Summary: Function that sends a request to determine the amount of races completed so far in a given season
#
# param year: number indicating what year to parse for
def get_max_races(year):
    global maxRace

    standingsType = getStandingsType()

    response = make_request(f'http://ergast.com/api/f1/{year}/last/{standingsType}')
    content = response.text
    root = ET.fromstring(content)
    lastRace = root.find(f".//{ns}StandingsTable")

    maxRace = int(lastRace.attrib["round"])
    return maxRace

# Summary: Function to build out array containing the names of each race in a season
#
# param year: number indicating what year to get the races from
def get_race_names(year):
    global totalRaces
    raceNames.clear()

    response = make_request(f'http://ergast.com/api/f1/{year}')
    content = response.text
    root = ET.fromstring(content)
    races = root.findall(f".//{ns}RaceTable/*")

    i = 1
    for race in races:
        raceName = race.find(f".//{ns}RaceName").text.replace(" Grand Prix", "") + " GP"
        raceNames[str(i)] = \
        {
            'label': raceName, 
            'style':
                {
                    'display': 'block', 'width': '50px', 'font-size': '7px', 'word-wrap': 'break-word', 'word-break': 'break-all', 'white-space': 'normal'
                }
        }
        i += 1

    totalRaces = (i - 1)


# Summary: Function used from callbacks to build out updated standings based on the new race or year
#
# param race: number indicating what race in the season should be parsed up to
# param year: number indicating what year to send requests for
def create_f1_figure(race, year):
    standingsType = "Drivers"
    if not driverStandings:
        standingsType = "Constructors"

    if FillDriversStandings(race, year): # If the standings are successfully initialized then fill it with the correct Points
        StandingsBuilder(race, year)

    df = pd.DataFrame(standings)
    fig = df.plot(
        title=f"{year} F1 {standingsType} Standings",
        labels=dict(index="Race", value="Points",
        variable=f"{standingsType[:-1]}", isinteractive="true"),
        markers=True,
        color_discrete_sequence=standingsTeamColours
    )

    for xy in standingsEliminated:
        fig.add_annotation(
            x=xy['x'],
            y=xy['y'],
            text="x",
            showarrow=False
        )
    
    fig.update_layout(
        xaxis = dict(
            tickmode = 'linear',
            dtick = 1
        )
    )
    evt.set()
    return fig

@app.callback(
    dash.dependencies.Output('f1-graph', 'figure'),
    [
        dash.dependencies.Input('f1-slider', 'value'),
        dash.dependencies.Input('f1-year', 'value'),
        dash.dependencies.Input('previousRace', 'n_clicks'),
        dash.dependencies.Input('nextRace', 'n_clicks'),
        dash.dependencies.Input('standingsToggle', 'n_clicks')
    ]
) # Update figure based on if the slider or year changes (either by year dial or prev next buttons)
def update_graph(races, year, prevClicks, nextClicks, toggleClicks):
    global driverStandings
    global loadedRaces

    evt.wait()

    if (races == None): # TODO this feels bad
        races = 1

    ctx = dash.callback_context
    if not ctx.triggered: # If no trigger then just use the values of year and value
        return create_f1_figure(races, year)

    trigger = ctx.triggered[0]['prop_id'].split('.')[0] # Gets the name of the id of the trigger
    if (trigger == "previousRace" and loadedRaces > 1):
        return create_f1_figure(loadedRaces - 1, year)
    elif (trigger == "nextRace" and loadedRaces != maxRace):
        return create_f1_figure(loadedRaces + 1, year)
    elif (trigger == "standingsToggle"):
        rootLogger.info("Standings type has be toggled. Clearing data.")
        driverStandings = not driverStandings
        clearStandings()
        return create_f1_figure(races, year)
    else:
        rootLogger.info("Fallback Path")
        return create_f1_figure(races, year)

@app.callback(
    dash.dependencies.Output('f1-slider', 'max'),
    [
        dash.dependencies.Input('f1-year', 'value')
    ]
) # Update the sliders max value when a new year is picked (the new race is a bit of a hack because it sometimes doesn't update)
def update_slider_max(year):
    get_max_races(year)
    return maxRace


@app.callback(
    dash.dependencies.Output('f1-slider', 'value'),
    [
        dash.dependencies.Input('f1-year', 'value'),
        dash.dependencies.Input('previousRace', 'n_clicks'),
        dash.dependencies.Input('nextRace', 'n_clicks')
    ]
) # Set the value to 1 every time the year changes
def update_slider_value(year, prevClicks, nextClicks): #year, 

    ctx = dash.callback_context
    if not ctx.triggered: # If no trigger then just set it to 1
        return 1

    trigger = ctx.triggered[0]['prop_id'].split('.')[0] # Gets the name of the id of the trigger
    if (trigger == "previousRace"):
        if (loadedRaces <= 1): return loadedRaces
        return loadedRaces - 1
    elif (trigger == "nextRace"):
        if (loadedRaces >= maxRace): return loadedRaces
        return loadedRaces + 1
    else:
        return 1

@app.callback(
    dash.dependencies.Output('f1-slider', 'marks'),
    [
        dash.dependencies.Input('f1-year', 'value')
    ]
) # Set the labels on the slider to the race names for the new season
def update_slider_labels(year):
    get_race_names(year)
    return raceNames

@app.callback(
    dash.dependencies.Output('standingsToggle', 'children'),
    [
        dash.dependencies.Input('standingsToggle', 'n_clicks'),
    ]
) # Toggle from drivers or constructors standings, update button's interior text accordingly
def change_toggle_label(clicks):
    global driverStandings
    if driverStandings:
        return "View Constructors Standings"
    else:
        return "View Drivers Standings"


if __name__ == '__main__':
    app.run_server()