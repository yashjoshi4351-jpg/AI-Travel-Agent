from pymongo import MongoClient
from datetime import datetime

# Connect MongoDB
client = MongoClient("mongodb://localhost:27017/")

db = client["ai_travel_agent"]
history_collection = db["search_history"]


# Save search
def save_search_history(user_query, result):

    history_data = {
        "query": user_query,
        "origin": result.get("origin"),
        "destination": result.get("destination"),
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "travelers": result.get("travelers"),
        "flights": result.get("flight_results"),
        "hotels": result.get("hotel_results"),
        "itinerary": result.get("itinerary"),
        "timestamp": datetime.now()
    }

    history_collection.insert_one(history_data)


# Get history
def get_history():

    history = history_collection.find().sort("timestamp", -1)

    results = []
    for item in history:
        results.append(item)

    return results


# Delete history
def delete_history(history_id):
    history_collection.delete_one({"_id": history_id})

def clear_history():
    history_collection.delete_many({})