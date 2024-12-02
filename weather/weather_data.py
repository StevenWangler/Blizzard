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
import yaml

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
    Extract relevant weather metrics for specific hours.
    
    Args:
        hourly_data: List of hourly weather data
        start_hour: Starting hour (24-hour format)
        end_hour: Ending hour (24-hour format)
        
    Returns:
        Dict containing processed weather data with probability weights
    """
    relevant_data = {}
    temp_trend = []
    precip_trend = []
    wind_trend = []
    visibility_trend = []
    
    # Probability weights for different factors
    weights = {
        'snow': 0.35,
        'temperature': 0.20,
        'wind': 0.20,
        'visibility': 0.15,
        'ground_conditions': 0.10
    }
    
    total_snow_probability = 0
    total_hours = 0
    
    for hour in hourly_data:
        hour_of_day = int(hour['time'].split()[1].split(':')[0])
        if start_hour <= hour_of_day < end_hour:
            total_hours += 1
            
            # Calculate weighted snow probability
            snow_factor = min(1.0, (hour['chance_of_snow'] / 100.0) * (float(hour.get('snow_cm', 0)) / 2.54) / 3.0)
            temp_factor = 1.0 if hour['temp_f'] < 20 else max(0, (32 - hour['temp_f']) / 12)
            wind_factor = min(1.0, hour['wind_mph'] / 35.0)
            vis_factor = max(0, 1.0 - (hour['vis_miles'] / 10.0))
            
            # Calculate hour probability
            hour_probability = (
                snow_factor * weights['snow'] +
                temp_factor * weights['temperature'] +
                wind_factor * weights['wind'] +
                vis_factor * weights['visibility']
            )
            
            total_snow_probability += hour_probability
            
            # Store detailed metrics
            relevant_data[f'hour_{hour_of_day}_probability'] = round(hour_probability * 100, 2)
            relevant_data[f'hour_{hour_of_day}_snow_factor'] = round(snow_factor * 100, 2)
            relevant_data[f'hour_{hour_of_day}_temp_factor'] = round(temp_factor * 100, 2)
            relevant_data[f'hour_{hour_of_day}_wind_factor'] = round(wind_factor * 100, 2)
            relevant_data[f'hour_{hour_of_day}_vis_factor'] = round(vis_factor * 100, 2)
            
            # Store original metrics
            relevant_data[f'hour_{hour_of_day}_temp_f'] = hour['temp_f']
            relevant_data[f'hour_{hour_of_day}_feelslike_f'] = hour['feelslike_f']
            relevant_data[f'hour_{hour_of_day}_windchill_f'] = hour['windchill_f']
            temp_trend.append(hour['temp_f'])
            
            # Precipitation metrics and accumulation
            relevant_data[f'hour_{hour_of_day}_chance_of_snow'] = hour['chance_of_snow']
            relevant_data[f'hour_{hour_of_day}_chance_of_rain'] = hour['chance_of_rain']
            relevant_data[f'hour_{hour_of_day}_snow_cm'] = hour.get('snow_cm', 0)
            relevant_data[f'hour_{hour_of_day}_precip_mm'] = hour.get('precip_mm', 0)
            relevant_data[f'hour_{hour_of_day}_precip_type'] = hour['condition']['text']
            precip_trend.append(hour.get('precip_mm', 0))
            
            # Wind conditions and trends
            relevant_data[f'hour_{hour_of_day}_wind_mph'] = hour['wind_mph']
            relevant_data[f'hour_{hour_of_day}_gust_mph'] = hour['gust_mph']
            relevant_data[f'hour_{hour_of_day}_wind_dir'] = hour['wind_dir']
            wind_trend.append(hour['wind_mph'])
            
            # Visibility and conditions
            relevant_data[f'hour_{hour_of_day}_visibility_miles'] = hour['vis_miles']
            relevant_data[f'hour_{hour_of_day}_cloud'] = hour['cloud']
            relevant_data[f'hour_{hour_of_day}_condition'] = hour['condition']['text']
            visibility_trend.append(hour['vis_miles'])
            
            # Ground and atmospheric conditions
            relevant_data[f'hour_{hour_of_day}_humidity'] = hour['humidity']
            relevant_data[f'hour_{hour_of_day}_pressure_in'] = hour['pressure_in']
            relevant_data[f'hour_{hour_of_day}_dewpoint_f'] = hour['dewpoint_f']
            relevant_data[f'hour_{hour_of_day}_will_it_snow'] = hour.get('will_it_snow', 0)
            relevant_data[f'hour_{hour_of_day}_will_it_rain'] = hour.get('will_it_rain', 0)
            relevant_data[f'hour_{hour_of_day}_uv'] = hour['uv']

    # Calculate trends
    if temp_trend:
        relevant_data['temp_trend'] = _calculate_trend(temp_trend)
        relevant_data['wind_trend'] = _calculate_trend(wind_trend)
        relevant_data['precip_trend'] = _calculate_trend(precip_trend)
        relevant_data['visibility_trend'] = _calculate_trend(visibility_trend)
        
        relevant_data['temp_min'] = min(temp_trend)
        relevant_data['temp_max'] = max(temp_trend)
        relevant_data['wind_peak'] = max(wind_trend)
        relevant_data['total_precip'] = sum(precip_trend)
    
    # Add overall probability metrics
    if total_hours > 0:
        relevant_data['average_snow_probability'] = round((total_snow_probability / total_hours) * 100, 2)
        relevant_data['max_hour_probability'] = round(max(
            relevant_data[k] for k in relevant_data.keys() if k.endswith('_probability')
        ), 2)
    
    return relevant_data

def _calculate_trend(values: List[float]) -> str:
    """Calculate the trend direction and magnitude of a series of values."""
    if not values or len(values) < 2:
        return "steady"
    
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]
    
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    
    diff = second_avg - first_avg
    
    if abs(diff) < 0.5:  # Small threshold for "steady"
        return "steady"
    elif diff > 0:
        return "increasing" if diff > 2 else "slightly increasing"
    else:
        return "decreasing" if diff < -2 else "slightly decreasing"

def get_relevant_weather_information(forecast_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process weather forecast data for snow day analysis.
    
    This function extracts weather data for the critical period between 7 PM
    and 8 AM the next day, which is typically when snow day decisions need to
    be made. It also includes weather alerts and pattern analysis.
    
    Args:
        forecast_data (Dict[str, Any]): Raw forecast data from WeatherAPI
    
    Returns:
        Dict[str, Any]: Processed weather data including:
            - Hourly metrics from 7 PM to midnight
            - Hourly metrics from midnight to 8 AM next day
            - Weather pattern analysis
            - Location-validated weather alerts
    """
    logging.debug('Getting relevant weather info from evening to next morning')
    weather_data = {}

    try:
        # Load district settings for location validation
        with open('config/district/settings.yaml', 'r') as f:
            district_settings = yaml.safe_load(f)
        
        county = district_settings['community']['county']
        city = district_settings['community']['city']
        state = district_settings['community']['state']
        
        # Process alerts and validate location relevance
        if 'alerts' in forecast_data:
            relevant_alerts = []
            for alert in forecast_data['alerts'].get('alert', []):
                alert_areas = alert.get('areas', '').lower()
                alert_regions = [area.strip() for area in alert_areas.split(';')]
                
                # Check if alert is relevant to our location
                is_relevant = any([
                    county.lower() in alert_areas,
                    city.lower() in alert_areas,
                    f"{city.lower()}, {state.lower()}" in alert_areas,
                    f"{county.lower()} county" in alert_areas
                ])
                
                if is_relevant:
                    relevant_alerts.append({
                        'title': alert.get('headline', ''),
                        'severity': alert.get('severity', ''),
                        'certainty': alert.get('certainty', ''),
                        'areas': alert.get('areas', ''),
                        'category': alert.get('category', ''),
                        'effective': alert.get('effective', ''),
                        'expires': alert.get('expires', ''),
                        'desc': alert.get('desc', '')
                    })
            
            weather_data['location_validated_alerts'] = relevant_alerts
            weather_data['alert_count'] = len(relevant_alerts)
        
        # Data from 7 PM to Midnight of the current day
        current_day_hourly = forecast_data['forecast']['forecastday'][0]['hour']
        evening_data = get_hourly_forecast_data(current_day_hourly, 19, 24)
        weather_data.update(evening_data)

        # Data from Midnight to 8 AM of the next day
        next_day_hourly = forecast_data['forecast']['forecastday'][1]['hour']
        morning_data = get_hourly_forecast_data(next_day_hourly, 0, 8)
        weather_data.update(morning_data)

        # Add location context
        weather_data['location'] = {
            'city': city,
            'county': county,
            'state': state,
            'coordinates': district_settings['community']['geographic_area']
        }

        return weather_data

    except Exception as e:
        logging.error(f"Error processing weather data: {str(e)}")
        raise 