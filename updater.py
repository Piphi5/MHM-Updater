from datetime import date, timedelta, datetime
import pandas as pd
import requests
import re
import numpy as np
import os

def to_int(x):
    try:
        return int(x)
    except ValueError:
        try:
            return int(re.sub(r".*-", "", x))
        except ValueError:
            return 0

def geolocational_filter(gps_lat, gps_lon, recorded_lat, recorded_lon):
    return ((recorded_lat == gps_lat and 
        recorded_lon == gps_lon) or
        isinstance(gps_lat, int) or
        isinstance(gps_lon, int)
        )


start_date = "2017-05-29"
end_date = date.today()
url = f"https://api.globe.gov/search/v1/measurement/protocol/measureddate/?protocols=mosquito_habitat_mapper&startdate={start_date}&enddate={end_date}&geojson=FALSE&sample=FALSE"
threshold = 10
anomaly_threshold = 1000

# downloads data from the GLOBE API
response = requests.get(url)

# Converts data into a useable dataframe
data = response.json()["results"]
        
df = pd.DataFrame(data)

# unpacking and joining the data entry
data_df = pd.DataFrame(df["data"].to_dict())
data_df = data_df.transpose()
df = df.join(data_df)
df.drop(["data"], axis=1, inplace = True)

# Geolocational Filtering (Remove data with poor geolocational quality)
vectorized_filter = np.vectorize(geolocational_filter)
bad_data = vectorized_filter(df["mosquitohabitatmapperMeasurementLatitude"].to_numpy(),
                             df["mosquitohabitatmapperMeasurementLongitude"].to_numpy(),
                             df["latitude"].to_numpy(),
                             df["longitude"].to_numpy()
                            )
df = df[~bad_data]
df = df.reset_index().drop(["index"], axis = 1)

# Remove suspected training events
suspect_df = df.groupby(by=['measuredDate','latitude','mosquitohabitatmapperWaterSource','siteName','longitude']).filter(lambda x: len(x) > threshold)
suspect_mask = df.isin(suspect_df)
clean_df = df[~suspect_mask].dropna(how = "all")

# Remove Anomolous Larvae counts
vectorized_int = np.vectorize(to_int)
clean_df["mosquitohabitatmapperLarvaeCount"] = vectorized_int(clean_df["mosquitohabitatmapperLarvaeCount"].fillna(0).values)
clean_df = clean_df[clean_df["mosquitohabitatmapperLarvaeCount"] < anomaly_threshold]

# create directory:
if not os.path.exists("Data"):
    os.mkdir("Data")

# write to file
clean_df.to_csv("Data/Clean Data.csv")

with open("Data/status.txt", "w+") as file:
    file.write("Last updated: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))