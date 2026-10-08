import json
import os

def build_data():
    with open('Rewari_32_Wards.geojson', 'r', encoding='utf-8') as f:
        wards_geojson = json.load(f)

    with open('Rewari_30_Cleaning_Circles.geojson', 'r', encoding='utf-8') as f:
        circles_geojson = json.load(f)

    with open('Rewari_SMP_Roads_Web.geojson', 'r', encoding='utf-8') as f:
        roads_geojson = json.load(f)

    # Master landmarks and daroga allotment records for all 30 circles
    landmark_daroga_info = {
        1: {'arterials': 'Delhi Road Corridor & Sector 4 Outer Ring', 'landmarks': 'Delhi Road, Hansi Road Link, Sector 4 Outer', 'daroga': 'Sunil Kumar', 'phone': '98120-41001', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1240, 'eq': '1 Tractor-Trolley, 8 Hand-Carts'},
        2: {'arterials': 'Dharuhera Road Radial & Northern Outskirts', 'landmarks': 'Dharuhera Road, Phidedi Bypass Link', 'daroga': 'Rajesh Sharma', 'phone': '98120-41002', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1235, 'eq': '1 Tipper, 8 Hand-Carts'},
        3: {'arterials': 'NH-919 Highway Corridor & Eastern Peripheral', 'landmarks': 'NH-919, Phidedi Approach Road', 'daroga': 'Vikram Singh', 'phone': '98120-41003', 'desig': 'Sanitary Daroga', 'sweepers': 11, 'target_m': 1275, 'eq': '1 Tractor-Trolley, 7 Hand-Carts'},
        4: {'arterials': 'Housing Board Colony & Sector 1 Main Road', 'landmarks': 'Housing Board Main Road, Delhi Road South', 'daroga': 'Satish Yadav', 'phone': '98120-41004', 'desig': 'Sanitary Daroga', 'sweepers': 11, 'target_m': 1280, 'eq': '1 Tipper, 8 Hand-Carts'},
        5: {'arterials': 'Subhash Basti & New Anaj Mandi North', 'landmarks': 'New Anaj Mandi Road, Railway Overbridge Approach', 'daroga': 'Rameshwar Dayal', 'phone': '98120-41005', 'desig': 'Sanitary Inspector', 'sweepers': 11, 'target_m': 1260, 'eq': '1 Tipper, 7 Hand-Carts'},
        6: {'arterials': 'Bawal Road Industrial Corridor & Sector 3', 'landmarks': 'Bawal Road, Sector 3 Main Road, NH-48 Link', 'daroga': 'Sanjay Kumar', 'phone': '98120-41006', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tractor-Trolley, 9 Hand-Carts'},
        7: {'arterials': 'Model Town South & Central Park Corridor', 'landmarks': 'Model Town Main Boulevard, Bawal Road North', 'daroga': 'Ashok Kumar', 'phone': '98120-41007', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1265, 'eq': '1 Tipper, 8 Hand-Carts'},
        8: {'arterials': 'Model Town Core Block A/B & Shopping Center', 'landmarks': 'Model Town Road, HUDA Complex', 'daroga': 'Rakesh Kumar', 'phone': '98120-41008', 'desig': 'Sanitary Inspector', 'sweepers': 12, 'target_m': 1260, 'eq': '1 Tipper, 9 Hand-Carts'},
        9: {'arterials': 'Brass Market & Commercial Plaza Hub', 'landmarks': 'Circular Road South, Brass Market Road, Jhajjar Road Link', 'daroga': 'Manoj Kumar', 'phone': '98120-41009', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1260, 'eq': '1 Auto-Tipper, 8 Hand-Carts'},
        10: {'arterials': 'Konsiwas Road & Southern Municipal Border', 'landmarks': 'Konsiwas Road, Railway Crossing Link', 'daroga': 'Naresh Kumar', 'phone': '98120-41010', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1265, 'eq': '1 Tractor-Trolley, 8 Hand-Carts'},
        11: {'arterials': 'Jhajjar Road North & Outer Octroi Zone', 'landmarks': 'Jhajjar Road, Subhash Nagar Main Road', 'daroga': 'Dinesh Yadav', 'phone': '98120-41011', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1290, 'eq': '1 Tipper, 8 Hand-Carts'},
        12: {'arterials': 'Western Bypass Corridor & Rampura Link', 'landmarks': 'Rewari Western Bypass, Rampura Road', 'daroga': 'Surender Singh', 'phone': '98120-41012', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tractor-Trolley, 8 Hand-Carts'},
        13: {'arterials': 'Mahendragarh Road & Rampura Gate', 'landmarks': 'Mahendragarh Highway, Rampura Flyover', 'daroga': 'Mukesh Kumar', 'phone': '98120-41013', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tipper, 8 Hand-Carts'},
        14: {'arterials': 'Kaluwas Approach & North-West Agricultural Ring', 'landmarks': 'Kaluwas Road, Western Bypass North', 'daroga': 'Ajay Sharma', 'phone': '98120-41014', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1230, 'eq': '1 Tractor-Trolley, 8 Hand-Carts'},
        15: {'arterials': 'Garhi Bolni Road & South-West Peripheral', 'landmarks': 'Garhi Bolni Road, Narnaul Road Link', 'daroga': 'Praveen Yadav', 'phone': '98120-41015', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tipper, 8 Hand-Carts'},
        16: {'arterials': 'Narnaul Road Corridor & Southern Spine', 'landmarks': 'Narnaul Highway, Railway Siding West', 'daroga': 'Amit Kumar', 'phone': '98120-41016', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1310, 'eq': '1 Tipper, 8 Hand-Carts'},
        17: {'arterials': 'Railway Station West & Rewari Jn Goods Yard', 'landmarks': 'Railway Station Road, Goods Shed Road', 'daroga': 'Deepak Saini', 'phone': '98120-41017', 'desig': 'Sanitary Inspector', 'sweepers': 12, 'target_m': 1305, 'eq': '2 Tippers, 10 Hand-Carts'},
        18: {'arterials': 'Rewari Bypass North & Anand Nagar', 'landmarks': 'Rewari Northern Bypass, Anand Nagar Road', 'daroga': 'Ravinder Kumar', 'phone': '98120-41018', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tipper, 8 Hand-Carts'},
        19: {'arterials': 'Old Court Road & Naiwali Sub-Sector', 'landmarks': 'Old Court Road, Naiwali Main Road', 'daroga': 'Pawan Kumar', 'phone': '98120-41019', 'desig': 'Sanitary Daroga', 'sweepers': 11, 'target_m': 1295, 'eq': '1 Auto-Tipper, 7 Hand-Carts'},
        20: {'arterials': 'Circular Road North Outer & Grain Market', 'landmarks': 'Circular Road North, Old Grain Market Road', 'daroga': 'Vijay Kumar', 'phone': '98120-41020', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tipper, 8 Hand-Carts'},
        21: {'arterials': 'Jhajjar Gate & Bada Bazaar North', 'landmarks': 'Jhajjar Gate Road, Bada Bazaar Main Street', 'daroga': 'Sohan Lal', 'phone': '98120-41021', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1245, 'eq': '1 Auto-Tipper, 8 Hand-Carts'},
        22: {'arterials': 'Gokal Gate & Nai Sarak Corridor', 'landmarks': 'Gokal Gate Road, Nai Sarak', 'daroga': 'Joginder Singh', 'phone': '98120-41022', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1245, 'eq': '1 Auto-Tipper, 8 Hand-Carts'},
        23: {'arterials': 'Ghanta Ghar & Dharuhera Gate Core', 'landmarks': 'Ghanta Ghar Chowk, Dharuhera Gate, Moti Chowk', 'daroga': 'Satyanarayan', 'phone': '98120-41023', 'desig': 'Sanitary Inspector', 'sweepers': 12, 'target_m': 1265, 'eq': '2 Auto-Tippers, 9 Hand-Carts'},
        24: {'arterials': 'Qutabpur & Balwal Gate Core', 'landmarks': 'Qutabpur Main Bazaar, Balwal Gate Road', 'daroga': 'Kailash Chand', 'phone': '98120-41024', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Auto-Tipper, 8 Hand-Carts'},
        25: {'arterials': 'Sarafa Bazaar & Old Mandi Central Hub', 'landmarks': 'Sarafa Bazaar, Main Chowk, Bartan Bazaar', 'daroga': 'Mahesh Kumar', 'phone': '98120-41025', 'desig': 'Sanitary Inspector', 'sweepers': 13, 'target_m': 1300, 'eq': '2 Auto-Tippers, 10 Hand-Carts'},
        26: {'arterials': 'Old Tehsil & Civil Hospital Zone', 'landmarks': 'Civil Hospital Road, Old Tehsil Complex', 'daroga': 'Subhash Chand', 'phone': '98120-41026', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1270, 'eq': '1 Tipper, 8 Hand-Carts'},
        27: {'arterials': 'Circular Road West Inner & Bara Hazari', 'landmarks': 'Circular Road West, Bara Hazari Road', 'daroga': 'Anil Kumar', 'phone': '98120-41027', 'desig': 'Sanitary Daroga', 'sweepers': 12, 'target_m': 1280, 'eq': '1 Tipper, 8 Hand-Carts'},
        28: {'arterials': 'Circular Road South-East & Kutubpur Outer', 'landmarks': 'Circular Road South, Delhi Road Junction', 'daroga': 'Krishan Lal', 'phone': '98120-41028', 'desig': 'Sanitary Daroga', 'sweepers': 13, 'target_m': 1250, 'eq': '1 Tractor-Trolley, 9 Hand-Carts'},
        29: {'arterials': 'South-Central Railway Colony & Loco Shed', 'landmarks': 'Loco Shed Road, Railway Colony Road', 'daroga': 'Baljeet Singh', 'phone': '98120-41029', 'desig': 'Sanitary Daroga', 'sweepers': 13, 'target_m': 1250, 'eq': '1 Tipper, 9 Hand-Carts'},
        30: {'arterials': 'South-East Radial & Industrial Bypass Link', 'landmarks': 'Konsiwas Road Junction, South Industrial Link', 'daroga': 'Rajender Prasad', 'phone': '98120-41030', 'desig': 'Sanitary Daroga', 'sweepers': 13, 'target_m': 1245, 'eq': '1 Tractor-Trolley, 9 Hand-Carts'}
    }

    # Attach rich operational attributes to circle GeoJSON features
    for feat in circles_geojson['features']:
        cid = int(feat['properties']['circle_id'])
        info = landmark_daroga_info.get(cid, {})
        feat['properties']['arterials'] = info.get('arterials', f'Circle {cid} Sector')
        feat['properties']['landmarks'] = info.get('landmarks', 'Main roads and ward boundaries')
        feat['properties']['daroga_name'] = info.get('daroga', 'Unassigned')
        feat['properties']['daroga_phone'] = info.get('phone', 'N/A')
        feat['properties']['daroga_desig'] = info.get('desig', 'Sanitary Daroga')
        feat['properties']['sweepers_count'] = info.get('sweepers', 12)
        feat['properties']['target_m_per_sweeper'] = info.get('target_m', 1250)
        feat['properties']['equipment'] = info.get('eq', '1 Tipper, 8 Hand-Carts')
        feat['properties']['shift'] = 'Morning (06:00 AM - 02:00 PM)'
        feat['properties']['full_title'] = f"Circle {cid:02d} - {info.get('arterials', '')}"

    # Save updated circle GeoJSON
    with open('Rewari_30_Cleaning_Circles.geojson', 'w', encoding='utf-8') as f:
        json.dump(circles_geojson, f, indent=2)

    # Re-export CSV with the rich daroga and landmark fields
    rows = []
    for feat in circles_geojson['features']:
        p = feat['properties']
        rows.append({
            'Circle_No': f"Circle {int(p['circle_id']):02d}",
            'Circle_Title': p['full_title'],
            'Main_Road_Boundaries': p['arterials'],
            'Key_Landmarks': p['landmarks'],
            'Road_Length_KM': p['road_length_km'],
            'Road_Segments': p['road_segments'],
            'Wards_Included': p['wards_included'],
            'Split_Status': p['is_ward_split'],
            'Daroga_Incharge': p['daroga_name'],
            'Designation': p['daroga_desig'],
            'Mobile_Number': p['daroga_phone'],
            'Sweepers_Deployed': p['sweepers_count'],
            'Daily_Target_Meters_Per_Sweeper': p['target_m_per_sweeper'],
            'Equipment_Vehicles': p['equipment'],
            'Shift': p['shift']
        })
    
    import pandas as pd
    pd.DataFrame(rows).to_csv('Rewari_30_Cleaning_Circles_Roster.csv', index=False)
    print("Saved: Rewari_30_Cleaning_Circles_Roster.csv")

    os.makedirs('js', exist_ok=True)
    with open('js/rewari-smp-data.js', 'w', encoding='utf-8') as f:
        f.write('/**\n * Rewari Municipal Council - SMP Roads, Wards, and 30 Cleaning Circles Embedded Data\n */\n')
        f.write('window.REWARI_WARDS = ' + json.dumps(wards_geojson) + ';\n\n')
        f.write('window.REWARI_DEFAULT_CIRCLES = ' + json.dumps(circles_geojson) + ';\n\n')
        f.write('window.REWARI_SMP_ROADS = ' + json.dumps(roads_geojson) + ';\n')

    print(f"js/rewari-smp-data.js generated successfully! Size: {os.path.getsize('js/rewari-smp-data.js') / (1024*1024):.2f} MB")

if __name__ == '__main__':
    build_data()
