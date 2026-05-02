# connect database
from Database import save_search_history

#Load Groq API Key
from pydantic import SecretStr

import os

GROQ_API_KEY  = os.getnv("GROQ")
Flight_Search_API = os.getnv("SERP")
Hotel_Search_API = os.getnv("SERP")

if GROQ_API_KEY:
  print("Groq API Key retrived!")
else:
  print("Please enter groq api key in colab secrets .")

if Flight_Search_API:
  print("Flight_Search_API retrived!")
else:
  print("Please enter Flight_Search_API in colab secrets .")



# Import Functions

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq



# Define Plannerstate

class PlannerState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage], "the messages in the conversation"]

    # User travel inputs
    origin: Optional[str]
    destination: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    travelers: Optional[int]

    # Tool outputs
    flight_results: Optional[List[dict]]
    hotel_results: Optional[List[dict]]

    # Final output
    itinerary: Optional[str]

    # Status tracking
    error: Optional[str]


# Initialize LLM

llm=ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.7,
    max_tokens=2000)


# Define Agents

#input agent

import json


def input_parser_agent(state: PlannerState):
    """LLM extracts details and converts cities to IATA codes."""
    last_message = state["messages"][-1].content

    prompt = f"""
    Extract trip details from this message: "{last_message}"

    CRITICAL INSTRUCTIONS:
    1. Convert city names to 3-letter IATA airport codes (e.g., 'New York' -> 'JFK', 'Delhi' -> 'DEL').
    2. Use YYYY-MM-DD for dates.
    3. 'end_date' is the return date.

    Return ONLY a JSON object:
    {{
        "destination": "IATA_CODE", 
        "origin": "IATA_CODE", 
        "start_date": "YYYY-MM-DD", 
        "end_date": "YYYY-MM-DD",
        "travelers": int
    }}
    If unknown, use null.
    """

    response = llm.invoke(prompt)
    content = response.content.strip().replace("```json", "").replace("```", "")
    extracted_data = json.loads(content)

    return {
        **state,
        "destination": extracted_data.get("destination"),
        "origin": extracted_data.get("origin"),
        "start_date": extracted_data.get("start_date"),
        "end_date": extracted_data.get("end_date"),
        "travelers": extracted_data.get("travelers", 1)
    }

# Flight Agent



import requests

def search_flights(origin: str, destination: str, date: str, return_date: str):


    FLIGHTAPI_KEY = Flight_Search_API.get_secret_value()

    search_url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_flights",
        "departure_id": origin,  # e.g. DEL
        "arrival_id": destination,  # e.g. BOM
        "outbound_date": date,  # YYYY-MM-DD
        "return_date": return_date,  # YYYY-MM-DD
        "currency": "INR",
        "api_key": FLIGHTAPI_KEY
    }


    response = requests.get(search_url, params=params)
    return response.json()

def flight_agent(state: PlannerState) ->PlannerState:

    origin = state.get("origin")
    destination = state.get("destination")
    date = state.get("start_date")
    return_date = state.get("end_date")

    try:

        results = search_flights(origin, destination, date, return_date)
        flights = results.get("best_flights", [])[:3]

        filtered_flights = []

        for flight in flights:
            filtered_flights.append({
                "airline": flight["flights"][0]["airline"],
                "departure": flight["flights"][0]["departure_airport"]["id"],
                "arrival": flight["flights"][0]["arrival_airport"]["id"],
                "price": flight.get("price"),
                "duration": flight.get("total_duration")
            })

        state["flight_results"] = filtered_flights
    except Exception as e:
        state["error"] = f"Flight search failed: {str(e)}"

    return state


# Hotel Agent

def search_hotels(city: str, checkin_date: str, checkout_date: str):
    HOTELAPI_KEY = Hotel_Search_API.get_secret_value()

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_hotels",
        "q": city,
        "check_in_date": checkin_date,
        "check_out_date": checkout_date,
        "currency": "INR",
        "hl": "en",
        "api_key": HOTELAPI_KEY
    }

    response = requests.get(url, params=params)
    return response.json()


def hotel_agent(state: PlannerState) ->PlannerState:
    city = state.get("origin")
    checkin_date = state.get("start_date")
    checkout_date = state.get("end_date")

    try:

        results = search_hotels(city, checkin_date, checkout_date)
        hotels = results.get("properties", [])[:3]

        filtered_hotels = []

        for hotel in hotels:
            filtered_hotels.append({
                "name": hotel["name"],
                "price": hotel.get("rate_per_night"),
                "rating": hotel.get("overall_rating")
            })

        state["hotel_results"] = filtered_hotels
    except Exception as e:
        state["error"] = f"Hotel search failed: {str(e)}"

    return state




# Itinerary Agent



def itinerary_agent(state: PlannerState) -> PlannerState:
    """
    Generate a travel itinerary using available flight and hotel .
    """

    # If there was a previous error, skip itinerary generation
    if state.get("error"):
        return state

    # Validate required inputs
    if not state.get("origin"):
        state["error"] = "Origin missing for itinerary generation."
        return state

    if not state.get("destination"):
        state["error"] = "Destination missing for itinerary generation."
        return state

    if not state.get("start_date") or not state.get("end_date"):
        state["error"] = "Travel dates missing for itinerary generation."
        return state

    try:
        # Prepare context for LLM
        flights = state.get("flight_results", "No flight data available")
        hotels = state.get("hotel_results")

        itinerary_prompt = f"""
        Create a detailed travel itinerary.

        Origin: {state['origin']}
        Destination: {state['destination']}
        Travel Dates: {state['start_date']} to {state['end_date']}
        Travelers:
        Number of Travelers: {state.get('travelers', 1)}

        Flight Options:
        {flights}
        
        Hotel Options:
        {hotels}


        Provide:
        - Day-wise plan
        - Recommended attractions
        - Travel tips
        - Budget awareness
        """

        response = llm.invoke(itinerary_prompt)

        state["itinerary"] = response.content
        state["error"] = None

    except Exception as e:
        state["error"] = str(e)
        state["itinerary"] = None

    return state

def error_handler(state: PlannerState) ->PlannerState:
    if state.get("error"):
        print("❌ Error:", state["error"])
    else:
        print("✅ Trip Planned Successfully!\n")
        print(state.get("itinerary"))
    return state



# Create the Graph



workflow: StateGraph[PlannerState] = StateGraph(PlannerState)

# Add nodes
workflow.add_node("input_parser", input_parser_agent)
workflow.add_node("flight_search", flight_agent)
workflow.add_node("hotel_search", hotel_agent)
workflow.add_node("itinerary_generator", itinerary_agent)
workflow.add_node("error_handler", error_handler)

# Set entry point
workflow.set_entry_point("input_parser")

# Define edges
workflow.add_edge("input_parser", "flight_search")
workflow.add_edge("flight_search", "hotel_search")
workflow.add_edge("hotel_search", "itinerary_generator")
workflow.add_edge("itinerary_generator", "error_handler")
workflow.add_edge("error_handler", END)

# Compile graph
app = workflow.compile()


def travel_agent(user_input: str):
    initial_state: PlannerState = {
        "messages": [HumanMessage(content=user_input)],
        "origin": None,
        "destination": None,
        "start_date": None,
        "end_date": None,
        "travelers": 1,
        "flight_results": None,
        "hotel_results": None,
        "itinerary": None,
        "error": None
    }

    # Run the graph
    final_output = app.invoke(initial_state)
    save_search_history(user_input, final_output)
    return final_output


if __name__ == "__main__":
    user_input = input("Enter query : ")
    print(travel_agent(user_input))
