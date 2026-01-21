import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_partners():
    """
    Scrapes partner data from logo.com.tr/logo-is-ortaklari by parsing the embedded __NEXT_DATA__ JSON.
    Iterates through pages until no more partners are found.
    """
    partners = []
    page = 1
    base_url = "https://www.logo.com.tr/logo-is-ortaklari"
    
    print("Starting partner scraping...")
    
    while True:
        try:
            url = f"{base_url}?page={page}"
            print(f"Fetching page {page}...")
            
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                print(f"Failed to fetch page {page}. Status code: {response.status_code}")
                break
                
            soup = BeautifulSoup(response.content, 'html.parser')
            next_data_tag = soup.find('script', id='__NEXT_DATA__')
            
            if not next_data_tag:
                print("Could not find __NEXT_DATA__ script tag.")
                break
                
            data = json.loads(next_data_tag.string)
            
            # Navigate the JSON structure to find the partners list
            # Based on typical Next.js props structure. We might need to adjust this path 
            # if the structure is different, but usually it's in props -> pageProps
            try:
                page_props = data.get('props', {}).get('pageProps', {})
                business_partner_data = page_props.get('businessPartnerData', {})
                
                partner_list = []
                if 'partners' in business_partner_data:
                    partner_list = business_partner_data['partners']
                    if isinstance(partner_list, dict) and 'items' in partner_list:
                         partner_list = partner_list['items']
                
                if not partner_list:
                    # If no partners are found, we assume we've reached the end of pagination
                    print(f"No partners found on page {page}. Stopping.")
                    break
                
                # Check for duplicates to prevent infinite loops (if the site just returns the last page over and over)
                if len(partner_list) > 0:
                    first_partner_id = partner_list[0].get('id')
                    if page > 1 and partners and partners[0].get('id') == first_partner_id:
                        print("Duplicate content detected (same as page 1). Stopping.")
                        break

                print(f"Found {len(partner_list)} partners on page {page}.")

                for p in partner_list:
                    name = p.get('name') or "İsimsiz"
                    email = p.get('email') or "Belirtilmemiş"
                    phone = p.get('phone') or "Belirtilmemiş"
                    web_address = p.get('webAddress') or ""
                    
                    # Location Logic
                    city = p.get('city') or ""
                    county = p.get('county') or "" # 'county' is the key in the JSON
                    
                    location_parts = []
                    if city: location_parts.append(city)
                    if county: location_parts.append(county)
                    
                    location = " / ".join(location_parts) if location_parts else "Belirtilmemiş"

                    partners.append({
                        "id": p.get('id'),
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "location": location,
                        "web_address": web_address,
                        "city": city,
                        "county": county
                    })
                
                page += 1
                time.sleep(0.5) # Politeness delay
                
            except Exception as e:
                print(f"Error parsing JSON on page {page}: {e}")
                break
                
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
            
    return partners

if __name__ == "__main__":
    # Test run
    data = scrape_partners()
    print(f"\nTotal Partners Scraped: {len(data)}")
