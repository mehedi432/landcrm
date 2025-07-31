# Copyright (c) 2025, Abdullah Al Mehedi and contributors
# For license information, please see license.txt

import frappe
import openai
import base64
import json
import random
import string
import requests
from frappe.model.document import Document

def encode_image_to_base64(image_filename):
    with open(image_filename, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def clean_openai_response(text: str) -> str:
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text.strip()

def generate_random_id(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def parse_address_components(components):
    data = {"city": None, "county": None, "state": None, "country": None, "zip_code": None}
    for comp in components:
        types = comp.get("types", [])
        if "locality" in types:
            data["city"] = comp.get("long_name")
        elif "administrative_area_level_2" in types:  # County
            data["county"] = comp.get("long_name")
        elif "administrative_area_level_1" in types:  # State
            data["state"] = comp.get("long_name")
        elif "country" in types:
            data["country"] = comp.get("long_name")
        elif "postal_code" in types:
            data["zip_code"] = comp.get("long_name")
    return data

def reverse_geocode(lat, lon, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        geo_data = response.json()
        if geo_data.get('results'):
            return geo_data['results'][0]
    return None

class TractProfile(Document):
    
    @frappe.whitelist()
    def extract_and_save_tract_data(self):
        if not self.tract_map_file:
            frappe.throw("Please upload a Map File in 'Tract Map File' field before extraction.")

        file_doc = frappe.get_doc("File", {"file_url": self.tract_map_file})
        image_path = file_doc.get_full_path()

        openai.api_key = frappe.conf.get("openai_api_key")
        if not openai.api_key:
            frappe.throw("OpenAI API key not configured in site_config.json")

        google_maps_api_key = frappe.conf.get("google_maps_api_key")
        if not google_maps_api_key:
            frappe.throw("Google Maps API key not configured in site_config.json")

        base64_image = encode_image_to_base64(image_path)

        prompt = (
            "This image is a map showing numbered land tracts with acreage values. "
            "Extract each tract number and its corresponding acres. "
            "Respond in JSON format like this:\n"
            "[{\"tract\": 1, \"acres\": 5.17}, {\"tract\": 2, \"acres\": 4.82}, ...]"
        )

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1500,
        )

        result_text = response.choices[0].message.content
        cleaned_text = clean_openai_response(result_text)

        try:
            tract_data = json.loads(cleaned_text)
        except Exception as e:
            frappe.throw(f"Failed to parse OpenAI response: {e}\n\nRaw response:\n{result_text}")

        frappe.logger().info(f"Extracted Tract Data: {json.dumps(tract_data, indent=2)}")
        print("\n--- Extracted Tract Data from OpenAI ---")
        print(json.dumps(tract_data, indent=2))
        print("----------------------------------------\n")

        # Clear existing tracts and fill with new data
        self.set("tracts", [])

        for tract in tract_data:
            random_tract_id = generate_random_id()
            self.append("tracts", {
                "tract_id": random_tract_id,
                "tract_name": f"Tract {tract.get('tract')}",
                "acres": float(tract.get("acres") or 0),
                "utilities_enabled": 0,
                "status": "Available",
            })

        self.status = "Processed"
        self.processed_on = frappe.utils.nowdate()
        self.save()
        frappe.db.commit()

        # Now, reverse geocode using parent's lat/lon and update all child tracts
        self.update_tracts_with_parent_location(google_maps_api_key)

        return tract_data

    def update_tracts_with_parent_location(self, google_maps_api_key):
        lat = self.latitude
        lon = self.longitude

        if lat is None or lon is None:
            frappe.msgprint("Parent latitude and longitude are not set, cannot reverse geocode.")
            return

        geo_result = reverse_geocode(lat, lon, google_maps_api_key)
        if not geo_result:
            frappe.msgprint("Reverse geocode failed for the provided latitude and longitude.")
            return

        address = geo_result.get("formatted_address", "")
        components = geo_result.get("address_components", [])
        parsed = parse_address_components(components)

        for row in self.tracts:
            row.address = address
            row.city = parsed.get("city") or ""
            row.county = parsed.get("county") or ""
            row.state = parsed.get("state") or ""
            row.country = parsed.get("country") or ""
            row.zip_code = parsed.get("zip_code") or ""

            print(f"[{row.tract_name}] Address: {address}")
            print(f" → City: {row.city}, County: {row.county}, State: {row.state}, Country: {row.country}, Zip: {row.zip_code}\n")

        self.save()
        frappe.db.commit()


