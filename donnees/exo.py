import matplotlib.pyplot as plt
import pandas as pd
db=pd.read_csv("ca-dealers-used-qc.csv")
fig, ax = plt.subplots()
ax.hist(db["price"], bins=50)
ax.set_title("Distribution des prix")
ax.set_xlabel("Prix ($)")
ax.set_ylabel("Nombre de voitures")

fig.savefig("exploration_prix-qc.png", dpi=150, bbox_inches="tight")