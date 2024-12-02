"""
Weather Data Module

This module handles weather data retrieval and processing for the snow day prediction system.
It interfaces with the WeatherAPI service to fetch weather forecasts and process them into
a format suitable for snow day analysis.

The module focuses on collecting weather data for the critical period between 7 PM and 8 AM,
which is typically when snow day decisions need to be made.

Classes:
    WeatherAPI: Handles API communication with WeatherAPI service

Functions:
    get_hourly_forecast_data: Extracts relevant weather metrics for specific hours
    get_relevant_weather_information: Processes forecast data for snow day analysis
"""

# Standard library imports
import logging
import os
from typing import Dict, Any, Optional, List

# Third-party imports
import requests
from dotenv import load_dotenv

class WeatherAPI:
    """
    WeatherAPI client for fetching weather forecast data.
    
    This class handles authentication and communication with the WeatherAPI service,
    providing methods to fetch weather forecasts including temperature, precipitation,
    wind conditions, and weather alerts.
    
    Attributes:
        api_key (str): WeatherAPI authentication key
        base_url (str): Base URL for WeatherAPI endpoints
        zip_code (str): ZIP code for weather location
    """

    def __init__(self):
        load_dotenv()  # Ensure .env is loaded
        self.api_key = os.getenv("WEATHER_API_KEY")
        if not self.api_key:
            logging.error("WEATHER_API_KEY not found in environment variables")
            raise ValueError("WEATHER_API_KEY not found in environment variables")
        logging.debug("WEATHER_API_KEY loaded successfully")
        
        self.base_url = "http://api.weatherapi.com/v1"
        self.zip_code = os.getenv("ZIP_CODE", "49341")
        logging.debug(f"Using ZIP code: {self.zip_code}")

    def get_forecast(self) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast for the current day and next day.
        
        Returns:
            Optional[Dict[str, Any]]: Weather forecast data including:
                - Hourly forecasts for 48 hours
                - Weather alerts if any
                - Current conditions
                Returns None if the request fails
        
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            url = (f'{self.base_url}/forecast.json'
                  f'?key={self.api_key}'
                  f'&q={self.zip_code}'
                  f'&days=2'
                  f'&aqi=no'
                  f'&alerts=yes')
            
            logging.debug(f"Making request to WeatherAPI with URL: {url.replace(self.api_key, '[REDACTED]')}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as ex:
            logging.error(f'Error in get_forecast: {ex}')
            return None

def get_hourly_forecast_data(hourly_data: List[Dict[str, Any]], 
                           start_hour: int, 
                           end_hour: int) -> Dict[str, Any]:
    """
    Extract relevant weather metrics for specified hours.
    
    Args:
        hourly_data (List[Dict[str, Any]]): List of hourly weather data
        start_hour (int): Starting hour (0-23)
        end_hour (int): Ending hour (0-23)
    
    Returns:
        Dict[str, Any]: Dictionary containing hourly weather metrics including:
            - Temperature and wind chill
            - Snow and rain probabilities
            - Wind speed and gusts
            - Visibility and cloud cover
            - Humidity and pressure
            - Weather conditions
    """
    relevant_data = {}
    for hour in hourly_data:
        hour_time = hour['time']
        hour_of_day = int(hour_time.split(' ')[1].split(':')[0])

        if start_hour <= hour_of_day < end_hour:
            # Temperature and feels-like metrics
            relevant_data[f'hour_{hour_of_day}_temp_f'] = hour['temp_f']
            relevant_data[f'hour_{hour_of_day}_feelslike_f'] = hour['feelslike_f']
            relevant_data[f'hour_{hour_of_day}_windchill_f'] = hour['windchill_f']
            
            # Precipitation chances
            relevant_data[f'hour_{hour_of_day}_chance_of_snow'] = hour['chance_of_snow']
            relevant_data[f'hour_{hour_of_day}_chance_of_rain'] = hour['chance_of_rain']
            relevant_data[f'hour_{hour_of_day}_snow_cm'] = hour.get('snow_cm', 0)
            
            # Wind conditions
            relevant_data[f'hour_{hour_of_day}_wind_mph'] = hour['wind_mph']
            relevant_data[f'hour_{hour_of_day}_gust_mph'] = hour['gust_mph']
            
            # Visibility and conditions
            relevant_data[f'hour_{hour_of_day}_visibility_miles'] = hour['vis_miles']
            relevant_data[f'hour_{hour_of_day}_cloud'] = hour['cloud']
            relevant_data[f'hour_{hour_of_day}_condition'] = hour['condition']['text']
            
            # Additional metrics
            relevant_data[f'hour_{hour_of_day}_humidity'] = hour['humidity']
            relevant_data[f'hour_{hour_of_day}_pressure_in'] = hour['pressure_in']
            relevant_data[f'hour_{hour_of_day}_dewpoint_f'] = hour['dewpoint_f']
            relevant_data[f'hour_{hour_of_day}_uv'] = hour['uv']

    return relevant_data

def get_relevant_weather_information(forecast_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process weather forecast data for snow day analysis.
    
    This function extracts weather data for the critical period between 7 PM
    and 8 AM the next day, which is typically when snow day decisions need to
    be made. It also includes any weather alerts that might affect the decision.
    
    Args:
        forecast_data (Dict[str, Any]): Raw forecast data from WeatherAPI
    
    Returns:
        Dict[str, Any]: Processed weather data including:
            - Hourly metrics from 7 PM to midnight
            - Hourly metrics from midnight to 8 AM next day
            - Weather alerts if any
    
    Raises:
        KeyError: If required data is missing from the forecast
    """
    logging.debug('Getting relevant weather info from evening to next morning')
    weather_data = {}

    try:
        # Data from 7 PM to Midnight of the current day
        current_day_hourly = forecast_data['forecast']['forecastday'][0]['hour']
        weather_data.update(get_hourly_forecast_data(current_day_hourly, 19, 24))

        # Data from Midnight to 8 AM of the next day
        next_day_hourly = forecast_data['forecast']['forecastday'][1]['hour']
        weather_data.update(get_hourly_forecast_data(next_day_hourly, 0, 8))

        # Get weather alerts if available
        if 'alerts' in forecast_data and forecast_data['alerts'].get('alert'):
            alert = forecast_data['alerts']['alert'][0]
            weather_data.update({
                'weather_alert_event': alert['event'],
                'weather_alert_severity': alert['severity'],
                'weather_alert_certainty': alert['certainty'],
                'weather_alert_urgency': alert['urgency'],
                'weather_alert_desc': alert['desc']
            })

    except KeyError as ex:
        logging.error('Key not found in forecast_data: %s', ex)

    return weather_data 