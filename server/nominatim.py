import requests

def get_location_from_coordinates(geo_location_str):
    try:
        lat, lng = geo_location_str.split(',')
        lat = lat.strip()
        lng = lng.strip()

        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&addressdetails=1"

        response = requests.get(url, headers={'User-Agent': 'C2App/1.0'})
        response.raise_for_status()

        data = response.json()

        address = data.get('address', {})
        country = address.get('country')
        city = address.get('city', address.get('town', address.get('village')))

        return country, city

    except ValueError:
        print(f"Error: Invalid geo_location format. Expected 'lat,lng' but got '{geo_location_str}'")
        return None

    except Exception as e:
        print(f"Error fetching location: {e}")
        return None

# Example usage:
# geo_location_str = "59.3293,18.0686"
# country, city = get_location_from_coordinates(geo_location_str)
# print(f"Country: {country}, City: {city}")
