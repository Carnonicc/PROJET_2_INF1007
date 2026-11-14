import pandas as pd
db=pd.read_csv("ca-dealers-used.csv")
colonnes = ["price", "miles", "year", "make", "model", "trim", "body_type",
            "drivetrain", "transmission", "fuel_type", "engine_size", "engine_block"]

# lignes avec les 12 colonnes remplies et au Quebec
condition = db[colonnes].notna().all(axis=1) & (db["state"] == "QC")

# un seul exemplaire par VIN, puis on garde seulement les 12 colonnes
resultat = db.loc[condition].drop_duplicates(subset="vin", keep="first")[colonnes]

resultat.to_csv("ca-dealers-used-qc.csv", index=False)
print(len(resultat))