import streamlit as st
import os
import sqlite3
import pandas as pd
import datetime
import io
from io import BytesIO
import pandas as pd
from PIL import Image
from sqlalchemy import text
import exifread
import tempfile

date = datetime.datetime.now()
today = date.strftime("%Y-%m-%d")
df_devices = pd.DataFrame()
df_components = pd.DataFrame()
df_history = pd.DataFrame()

st.set_page_config(page_title= "HC Hardware",
                   page_icon= "💻",
                   initial_sidebar_state="auto",
                   layout="wide",
                   menu_items={
                       'Get Help':None,
                       'Report a Bug':None,
                       "About":'''### [F&B Hardware Inventory v2.0.0](https://github.com/JAndrewGibson/inventory_management)   
POS tracking software by [Andrew Gibson](https://github.com/JAndrewGibson) - Last updated: 4/19/23  
### New features:
- Images re-implemented from the ground up!
- - All images are now stored in the folder itself for optimization and every type of entry can accept an image
- Database template has been updated to reflect the change!
- Fixed component selection - it is now independent from the device page entirely
- Added links in the about page as well as the overview and sidebar

### Roadmap:
- A new page to view all locations and device/component types
- Remove hardcoded "pos options", which only allows for SpotOn, Tapin2, Toast and Mashgin.
- Implement QR code system
- Ability to use a checkbox to affect changes on the component when changing device.
- After editing components and devices, success box needs to be moved to the top of the page

### Previous changes:

##### V1.0 (3/4/24)
- Both all filtering dropdown boxes are multi-select boxes (finally)
- All of the database connections are now cached until the refresh button is selected
- Filtering no longer affects the editing dropdown fields
- New template for Github (including history and all new changes!)
- Removed the photos from the history table
- If notes are left blank, they now return a None-type object

##### V0.4 (2/13/24)
- Caching has now been added!
  - Hopefully this will speed up the database!
- Converted to streamlit SQL rather than basic SQLite
- Image optimization has also been added (needs more work)
- All warnings now appear at the top of the page.
  - Previously warnings from the sidebar

##### V0.3 (2/5/24)
- There is now a history page!
  - A new history entry is added everytime a change is made to the database
  - Timestamps are on everything, including a 'last edit' parameter on every device.
- The ability to download the database as an excel spreadsheet has been added to the sidebar.
  - History is now included in the download
- Added a form to add new locations!


##### V0.2 (2/2/24)
- There is now a component page!
- There are now forms to add components AND devices!
- Components and devices are now fully seperated and show their connections to eachother!
- There's a template for the database for anyone else who wants to copy the project.
- Added photo support (needs compression algorithm for space-saving)

##### V0.1 (1/15/24)
- Added device page and connected it to a SQL database!
'''

                       })

database_file = "POSHardware.db"
absolute_path = os.path.dirname(__file__)
IMAGES_DIR = "images"

def process_and_save_image(image_upload, sn):
    images_folder = "images"
    os.makedirs(images_folder, exist_ok=True)

    _, original_extension = os.path.splitext(image_upload.name)
    original_extension = original_extension.lower()

    image_path = os.path.join(images_folder, f"{sn}.jpg")

    try:
        image = Image.open(image_upload)

        if original_extension not in (".jpg", ".jpeg"):
            image = image.convert('RGB')

        image.save(image_path, format='JPEG', quality=50)
        return os.path.basename(image_path)

    except OSError as e:
        st.error(f"Error processing image: {e}")
        return None

def refresh_data():
    st.cache_data.clear()
    print("Data Refreshed!")

conn = st.connection(name="connection", type="sql", url="sqlite:///" + os.path.join(absolute_path, database_file))

hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

st.title("HC Hardware")

def download_excel():
    # Read data from the DEVICES table into a DataFrame
    df_devices = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, `FRIENDLY NAME`, NOTES, `LAST EDIT` FROM DEVICES;")
    df_history = conn.query("SELECT `CHANGE TIME`, `PREVIOUS LOCATION`, `PREVIOUS FRIENDLY NAME`, `PREVIOUS CONNECTION`, `PREVIOUS NOTES`, `NEW LOCATION`, `NEW FRIENDLY NAME`, `NEW CONNECTION`, `NEW NOTES` FROM HISTORY;")
    df_components = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, CONNECTED, NOTES, `LAST EDIT` FROM COMPONENTS;")
    print("Retreiving Data!")
    # Convert DataFrames to Excel with two sheets
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df_devices.to_excel(writer, sheet_name='DEVICES', index=False)
        df_components.to_excel(writer, sheet_name='COMPONENTS', index=False)
        df_history.to_excel(writer, sheet_name="HISTORY", index=False)

    # Save the Excel data to a BytesIO buffer
    excel_data.seek(0)
    print("Saved Sucessfully!")
    return excel_data

@st.cache_data
def fetch_data(table_name):
    query = f"SELECT * FROM {table_name};"
    result = conn.query(query)
    return result


def get_serial_number(friendly_name):
    device_row = df_devices[df_devices['FRIENDLY NAME'] == friendly_name]
    if not device_row.empty:
        return device_row.iloc[0]['S/N']
    else:
        return None  # Handle case where no matching device is found

df_devices = fetch_data("DEVICES").sort_values(by='LAST EDIT', ascending=False)
df_components = fetch_data("COMPONENTS").sort_values(by='LAST EDIT', ascending=False)
df_history = fetch_data("HISTORY")
df_locations = fetch_data("LOCATIONS")
df_device_types = fetch_data("DEVICE_TYPES")
df_component_types = fetch_data("COMPONENT_TYPES")

# Sidebar menu
st.sidebar.title("Actions")

if st.sidebar.button("Refresh data"):
    refresh_data()
    
# Download the Excel file
st.sidebar.download_button(
    label="Download as Excel",
    data=download_excel(),
    file_name=f"{today} POS Hardware Inventory.xlsx",
    key="download_excel_button"
)

existing_locations = list(df_locations['LOCATION'].unique())
existing_devices = [name for name in df_devices['FRIENDLY NAME'].unique() if name is not None and name.strip() != ""]
existing_device_types = list(df_device_types['DEVICE_TYPE'].unique())
existing_component_types = list(df_component_types['COMPONENT_TYPE'].unique())

# Form to add a new device
with st.sidebar.expander("**Add Device**"):
    with st.form("Add New Device"):
        pos_options = ["SpotOn", "Tapin2", "Toast", "Mashgin", "None"]
        device_pos = st.selectbox("POS", [""] + pos_options)
        device_sn = st.text_input("S/N (Serial Number)", "", key="device_sn")
        device_location = st.selectbox("Location", [""] + existing_locations)
        device_type = st.selectbox("Type", [""] + existing_device_types)
        device_friendly_name = st.text_input("Friendly Name", "")
        device_notes = st.text_input("Notes", "None")

        # File upload for new device image
        device_image_upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])

        # Submit button
        add_device_submit = st.form_submit_button("Add Device")

with st.sidebar.expander("**Add Component**"):
    with st.form("Add New Component"):
        pos_options = ["SpotOn", "Tapin2", "Toast", "Mashgin", "None"]
        component_pos = st.selectbox("POS", [""] + pos_options)
        component_sn = st.text_input("S/N (Serial Number)", "", key="component_sn")
        component_location = st.selectbox("Location", [""] + existing_locations)
        component_type = st.selectbox("Type", [""] + existing_component_types)
        component_connected = st.selectbox("Connected",[""] + existing_devices)
        component_notes = st.text_input("Notes", "None")

        # File upload for new component image
        component_image_upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])

        # Submit button
        add_component_submit = st.form_submit_button("Add Component")

with st.sidebar.expander("**Add Location**"):
    with st.form("Add New Location"):
        location_name = st.text_input("Location Name", "")

        # File upload for new location image
        location_image_upload = st.file_uploader("Upload a photo for the Image", type=["jpg", "jpeg", "png"])
        
        if location_image_upload:
            st.image(location_image_upload)

        # Submit button
        add_location_submit = st.form_submit_button("Add Location")
        
with st.sidebar.expander("**Add Device Type**"):
    with st.form("Add New Device Type"):
        device_type_name = st.text_input("Device Type Name", "")

        # File upload for new device type image
        device_type_image_upload = st.file_uploader("Upload a photo for the image", type=["jpg", "jpeg", "png"])
        
        if device_type_image_upload:
            st.image(device_type_image_upload)

        # Submit button
        add_device_type_submit = st.form_submit_button("Add Device Type")
        
with st.sidebar.expander("**Add Component Type**"):
    with st.form("Add New Component Type"):
        component_type_name = st.text_input("Component Type Name", "")

        # File upload for new component type image
        component_type_image_upload = st.file_uploader("Upload a photo for the image", type=["jpg", "jpeg", "png"])
        
        if component_type_image_upload:
            st.image(component_type_image_upload)

        # Submit button
        add_component_type_submit = st.form_submit_button("Add Component Type")

# Process the form submission
if add_device_submit:
    # Validate and process the form data
    if device_sn and device_pos and device_location and device_type:
        if device_notes == "None" or "":
            device_notes = None

        try:
            if device_image_upload:
                device_image_filename = process_and_save_image(device_image_upload, device_sn)
            else:
                device_image_filename = None

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_query = text("INSERT INTO DEVICES (`S/N`, POS, LOCATION, `TYPE`, `FRIENDLY NAME`, NOTES, IMAGE, `LAST EDIT`) VALUES (:a, :b, :c, :d, :e, :f, :g, :h);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g);")
            with conn.session as session:
                session.execute(insert_query, {"a": device_sn, "b": device_pos, "c": device_location, "d": device_type, "e": device_friendly_name, "f": device_notes, "g": device_image_filename, "h": timestamp})
                session.execute(insert_history_query, {"a": timestamp, "b": device_sn, "c": device_location, "d": device_friendly_name, "e": device_notes, "f": device_image_filename, "g": "NEW DEVICE"})
                session.commit()

            st.success(f"A new {device_type} ({device_friendly_name}) was added successfully to {device_location}!")

            # Refresh the data in the app
            print("New Device Added")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new device: {e}")
    else:
        st.warning("Please fill out all required fields for device entry (S/N, POS, Location and Type).")

if add_component_submit:
    # Validate and process the form data
    if component_sn and component_pos and component_location and component_type:
        if component_notes == "None" or "":
            component_notes = None
        try:
            if component_image_upload:
                component_image_filename = process_and_save_image(component_image_upload, component_sn)
            else:
                component_image_filename = None

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_query = text("INSERT INTO COMPONENTS (POS, `TYPE`, `S/N`, LOCATION, CONNECTED, NOTES, IMAGE, `LAST EDIT`) VALUES (:a, :b, :c, :d, :e, :f, :g, :h);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g);")

            # Execute the query
            with conn.session as session:
                session.execute(insert_query, {"a": component_pos, "b": component_type, "c": component_sn, "d": component_location, "e": get_serial_number(component_connected), "f": component_notes, "g": component_image_filename, "h": timestamp})
                session.execute(insert_history_query, {"a": timestamp, "b": component_sn, "c": component_location, "d": get_serial_number(component_connected), "e": component_notes, "f": component_image_filename, "g": "NEW COMPONENT"})
                session.commit()
                        
            st.success(f"A new {component_type} ({component_sn}) was added successfully to {component_location}!")

            # Refresh the data in the app
            print("New Component Added")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.error(f"Error adding new component: {e}")
    else:
        st.warning("Please fill out all required fields for component entry (S/N, POS, Location and Type).")

if add_location_submit:
    # Validate and process the form data
    if location_name:
        try:
            if location_image_upload:
                location_image_filename = process_and_save_image(location_image_upload, location_name)
            else:
                location_image_filename = None

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute the query
            insert_query = text("INSERT INTO LOCATIONS (LOCATION, IMAGE) VALUES (:a, :b);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW LOCATION', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d);")

            with conn.session as session:
                session.execute(insert_query, {"a": location_name, "b": location_image_filename})
                session.execute(insert_history_query, {"a": timestamp, "b": location_name, "c": location_image_filename, "d": "NEW LOCATION"})
                session.commit()

            st.success(f"{location_name} has been created as a new location!")

            # Refresh the data in the app
            print("New Location Added")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new location: {e}")
    else:
        st.warning("Please name your location.")
        
if add_device_type_submit:
    # Validate and process the form data
    if device_type_name:
        try:
            if device_type_image_upload:
                device_type_image_filename = process_and_save_image(device_type_image_upload, device_type_name)
            else:
                device_type_image_filename = None

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute the query
            insert_query = text("INSERT INTO 'DEVICE_TYPES' (DEVICE_TYPE, IMAGE) VALUES (:a, :b);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c);")
            change_log_text = f"NEW DEVICE TYPE: {device_type_name}"

            
            with conn.session as session:
                session.execute(insert_query, {"a": device_type_name, "b": device_type_image_filename})
                session.execute(insert_history_query, {"a": timestamp, "b": device_type_image_filename, "c": change_log_text})
                session.commit()

            st.success(f"{device_type_name} has been created as a new device type!")

            # Refresh the data in the app
            print("New Device Type Added!")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new device type: {e}")
    else:
        st.warning("Please enter the type of device you need to record.")
        
if add_component_type_submit:
    # Validate and process the form data
    if component_type_name:
        try:
            if component_type_image_upload:
                component_type_image_filename = process_and_save_image(component_type_image_upload, component_type_name)
            else:
                component_type_image_filename = None


            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute the query
            insert_query = text("INSERT INTO 'COMPONENT_TYPES' (COMPONENT_TYPE, IMAGE) VALUES (:a, :b);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c);")
            change_log_text = f"NEW COMPONENT TYPE: {component_type_name}"

            
            with conn.session as session:
                session.execute(insert_query, {"a": component_type_name, "b": component_type_image_filename})
                session.execute(insert_history_query, {"a": timestamp, "b": component_type_image_filename, "c": change_log_text})
                session.commit()

            st.success(f"{component_type_name} has been created as a new component type!")

            # Refresh the data in the app
            print("New Component Type Added!")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new component type: {e}")
    else:
        st.warning("Please enter the type of component you need to record.")

# Sidebar content
st.sidebar.markdown("##### [This software was created independently by Andrew Gibson outside of work hours.](https://github.com/JAndrewGibson/inventory_management)")

overview, devices, components, history = st.columns(4)

overview, devices, components, history = st.tabs(["Overview", "Devices", "Components", "History"])

with overview:
    col1, col2 = st.columns(2)
    col1.subheader('Overview')
    
    # Count the number of changes in the last 24 hours
    df_history['CHANGE TIME'] = pd.to_datetime(df_history['CHANGE TIME'])
    twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
    changes_last_24_hours = df_history[df_history['CHANGE TIME'] >= twenty_four_hours_ago].shape[0]
    if changes_last_24_hours == 1:
        changes_sentence = "There has only been one change"
    elif changes_last_24_hours > 1:
        changes_sentence = f"There have been {changes_last_24_hours} changes"
    else:
        changes_sentence = "Looking good! There have not been any changes"
    
    # Count the number without a photo
    total_devices = df_devices["S/N"].count()
    total_components = df_components["S/N"].count()
    wasted_devices = df_devices[df_devices['LOCATION'] == 'E-WASTED']['LOCATION'].count()
    wasted_components = df_components[df_components['LOCATION'] == 'E-WASTED']['LOCATION'].count()
    #devices_without_photo = df_devices['IMAGE'].isnull().sum()
    #components_without_photo = df_components['IMAGE'].isnull().sum()
    stored_assets = df_devices[df_devices['LOCATION'] == 'WAREHOUSE']['LOCATION'].count() + (df_components[df_components['LOCATION'] == 'WAREHOUSE']['LOCATION'].count()) + (df_devices[df_devices['LOCATION'] == "JACK DANIEL'S OFFICE"]['LOCATION'].count()) + (df_components[df_components['LOCATION'] == "JACK DANIEL'S OFFICE"]['LOCATION'].count())
    unknown_assets = df_devices[df_devices['LOCATION'] == 'UNKNOWN']['LOCATION'].count() + (df_components[df_components['LOCATION'] == 'UNKNOWN']['LOCATION'].count())    
        
    # Display the paragraph
    col1.write(f'''
               {changes_sentence} to the database in the last 24 hours.
               
               Right now there are {total_devices-wasted_devices} active devices and {total_components-wasted_components} components.
               {stored_assets} assets are currently in storage, {unknown_assets} are in an unknown location, and {wasted_devices + wasted_components} assets have been sent to E-Waste.
               
               Got ideas for what should be displayed on this page? [Tell Andrew](https://github.com/JAndrewGibson)!
               ''')
    
    location_data = df_devices.groupby("LOCATION")["S/N"].nunique().reset_index()
    POS_data = df_devices.groupby("POS")["S/N"].nunique()
    
    # Display the data in a table
    col2.subheader("Location Breakdown")
    col2.dataframe(location_data, hide_index=True, use_container_width=True,)
    col1.dataframe(POS_data)

with devices:
    col1, col2 = st.columns(2)
    col1.subheader('Devices')
   
    device_locations_list = ['All'] + list(existing_locations)
    selected_device_locations = col1.multiselect("Select a location", device_locations_list, default=["All"])
    device_type_list = ['All'] + list(existing_device_types)
    selected_types = col1.multiselect("Select a type", device_type_list, default=["All"])
    # Search bar for device lookup
    search_device = col1.text_input("Search for a device", "")

    # Filter devices based on search input and selected location
    filtered_devices = df_devices.copy()
    if "All" not in selected_device_locations:
        filtered_devices = filtered_devices[filtered_devices['LOCATION'].isin(selected_device_locations)]
    if "All" not in selected_types:
        filtered_devices = filtered_devices[filtered_devices['TYPE'].isin(selected_types)]
    if search_device:
        filtered_devices = filtered_devices[filtered_devices.apply(lambda row: any(row.astype(str).str.contains(search_device, case=False)), axis=1)]

    # Display filtered devices in a DataFrame
    if not filtered_devices.empty:
        col1.dataframe(filtered_devices, use_container_width=True, hide_index=True, column_order=("POS", "TYPE", "LOCATION","FRIENDLY NAME", "NOTES", "S/N","LAST EDIT"))
    
      
        col2.subheader('Edit Device')
        # Dropdown to select a device from the filtered list
        available_devices = filtered_devices.apply(
        lambda row: f"{row['FRIENDLY NAME']} at {row['LOCATION']}",axis=1).tolist()
        # Create a mapping between display names and serial numbers
        display_name_to_serial = {display_name: serial for display_name, serial in zip(available_devices, filtered_devices['S/N'].tolist())}

        # Dropdown to select a device from the filtered list
        selected_device_display = col2.selectbox("Select a device to edit", available_devices)

        # Get the corresponding serial number based on the displayed name
        selected_device_serial = display_name_to_serial.get(selected_device_display, None)

        connected_components = df_components[df_components['CONNECTED'] == selected_device_serial]['TYPE'].unique()
        connected_components_text = " ".join(f'<span style="color:green">•</span> {component}' for component in connected_components)
        col2.markdown(connected_components_text, unsafe_allow_html=True)
        
        # Display editable fields
        if not filtered_devices.empty:
            print("Filtering Devices...")
            selected_device_index = filtered_devices[filtered_devices['S/N'] == selected_device_serial].index[0]

            # Editable Fields            
            pos_options = df_devices['POS'].unique()
            pos = col2.selectbox("Device POS", pos_options, index=pos_options.tolist().index(filtered_devices.at[selected_device_index, 'POS']))
            location_options = df_devices['LOCATION'].unique()
            location = col2.selectbox("Device Location", location_options, index=location_options.tolist().index(filtered_devices.at[selected_device_index, 'LOCATION']))
            friendly_name = col2.text_input("Friendly Name", filtered_devices.at[selected_device_index, 'FRIENDLY NAME'])
            notes = col2.text_input("Device Notes", filtered_devices.at[selected_device_index, 'NOTES'])
            # Display existing image if available
            if 'IMAGE' in filtered_devices.columns:
                existing_image_filename = filtered_devices.at[selected_device_index, 'IMAGE']
                if existing_image_filename:
                    images_folder = "images" 
                    full_image_path = os.path.join(images_folder, existing_image_filename)

                    if os.path.exists(full_image_path):
                        col2.image(full_image_path, width=200) 
                    else:
                        col2.warning("Image filename found in database but the file itself was not found. It may have been deleted.")
                        
            # File upload for image in the right column
            image_upload = None
            image_upload = col2.file_uploader("Upload a new photo?", type=["jpg", "jpeg", "png"])

            save_changes_to_connected = col2.checkbox("Save changes to connected components.", value=False, label_visibility="visible")

            if col2.button("Save Device"):
                try:
                    # Fetch the current values before the update
                    fetch_old_values_query = "SELECT POS, LOCATION, `FRIENDLY NAME`, NOTES, IMAGE FROM DEVICES WHERE `S/N` = :a;"
                    old_values = conn.query(fetch_old_values_query, params={"a": selected_device_serial})
                    
                    if notes == "None":
                        notes = None
                    if friendly_name == "None":
                        friendly_name = None
                    
                    if image_upload:
                        device_image_filename = process_and_save_image(image_upload, selected_device_serial)
                    else:
                        device_image_filename = None
                    
                    # Update the data in the SQL database
                    update_query = text(f"UPDATE DEVICES SET POS = :a, LOCATION = :b, `FRIENDLY NAME` = :c, NOTES = :d, IMAGE = :e, `LAST EDIT` = :f WHERE `S/N` = :g;")
                    insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS FRIENDLY NAME', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW NOTES', 'NEW PHOTO','CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g, :h, :i, :j, :k);")
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with conn.session as session:
                        session.execute(update_query, {"a": pos, "b": location, "c": friendly_name, "d": notes, "e": device_image_filename, "f": timestamp, "g": selected_device_serial})
                        session.execute(insert_history_query, {"a": timestamp, "b": selected_device_serial, "c": old_values.iat[0, 1], "d": old_values.iat[0, 2], "e": old_values.iat[0, 3], "f": old_values.iat[0, 4], "g": location, "h": friendly_name, "i": notes, "j": device_image_filename, "k": "DEVICE UPDATE"})
                        session.commit()
                    
                    st.success("Changes saved successfully!")
                    print("Changes saved successfully!")
                    # Refresh the data in the app
                    refresh_data()

                except sqlite3.Error as e:
                    st.error(f"Error updating data: {e}")
    else:
        col1.write("Oops, no devices... Check your search terms or refresh data!")
            
with components:
    col1, col2 = st.columns(2)
    col1.subheader('Components')
   
    component_locations_list = ['All'] + list(existing_locations)
    selected_component_locations = col1.multiselect("Select a location", component_locations_list, default=['All'], key="component_location_select")
    component_type_list = ['All'] + list(df_components['TYPE'].unique())
    selected_list = col1.multiselect("Select a type", component_type_list, default=['All'], key="component_type_select")
    search_components = col1.text_input("Search for a component", "")

    # Filter components based on search input and selected location
    if 'All' in selected_component_locations:
        filtered_components = df_components  # Show all components for now
        if 'All' not in selected_list:
            filtered_components = filtered_components[filtered_components['TYPE'].isin(selected_list)]
    else:
        filtered_components = df_components[df_components['LOCATION'].isin(selected_component_locations)]

    # Apply type filtering regardless of location selection (if 'All' types not selected)
    if 'All' not in selected_list:
        filtered_components = filtered_components[filtered_components['TYPE'].isin(selected_list)]

    if search_components:
        filtered_components = filtered_components[filtered_components.apply(lambda row: any(row.astype(str).str.contains(search_components, case=False)), axis=1)]


    # Display filtered components in a DataFrame
    col1.dataframe(filtered_components, use_container_width=True, hide_index=True, column_order=("POS", "TYPE", "LOCATION", "CONNECTED", "NOTES", "S/N","LAST EDIT"))
      
    col2.subheader('Edit Component')
    # Dropdown to select a component from the filtered list
    available_components = []
    if not filtered_components.empty:  # Check if DataFrame is not empty
        available_components = filtered_components.apply(lambda row: f"{row['TYPE']} at {row['LOCATION']}", axis=1).tolist()
    # Create a mapping between display names and serial numbers
    display_name_to_serial = {display_name: serial for display_name, serial in zip(available_components, filtered_components['S/N'].tolist())}
    serial_to_display_name = {serial: display_name for serial, display_name in zip(available_components, filtered_components['S/N'].tolist())}

    # Dropdown to select a component from the filtered list
    selected_component_display = col2.selectbox("Select a component to edit", available_components)
    friendly_name_to_serial = df_devices.set_index('FRIENDLY NAME')['S/N'].to_dict()
    # Get the corresponding serial number based on the displayed name
    selected_component_serial = display_name_to_serial.get(selected_component_display, None)

    # Display editable fields
    if not filtered_components.empty:
        print("Filtering Components...")
        selected_component_index = filtered_components[filtered_components['S/N'] == selected_component_serial].index[0]

        # Add editable fields to the left column
        pos_options = df_components['POS'].unique()
        pos = col2.selectbox("Component POS", pos_options, index=pos_options.tolist().index(filtered_components.at[selected_component_index, 'POS']))
        location_options = df_components['LOCATION'].unique()
        location = col2.selectbox("Component Location", location_options, index=location_options.tolist().index(filtered_components.at[selected_component_index, 'LOCATION']))
        
        # Get current component connection
        current_connection_serial = filtered_components.at[selected_component_index, 'CONNECTED']
        current_connection = df_devices[df_devices['S/N'] == current_connection_serial]['FRIENDLY NAME'].iloc[0] if current_connection_serial else None
        connection_options = df_devices['FRIENDLY NAME'].unique()
        default_connection_index = connection_options.tolist().index(current_connection) if current_connection in connection_options else None
        connection = col2.selectbox("Component Connection", connection_options, index=default_connection_index)
        notes = col2.text_input("Component Notes", filtered_components.at[selected_component_index, 'NOTES'])
        # Display existing image if available
        
        if 'IMAGE' in filtered_components.columns:
                existing_image_filename = filtered_components.at[selected_component_index, 'IMAGE']
                if existing_image_filename:
                    images_folder = "images" 
                    full_image_path = os.path.join(images_folder, existing_image_filename)

                    if os.path.exists(full_image_path):
                        col2.image(full_image_path, width=200) 
                    else:
                        col2.warning("Image filename found in database but the file itself was not found. It may have been deleted.")
                
        # File upload for image in the right column
        image_upload = None
        image_upload = col2.file_uploader("Upload a photo?", type=["jpg", "jpeg", "png"])
        
        selected_connection_serial = friendly_name_to_serial.get(connection)
        if col2.button("Save Component"):
            try:
                # Fetch the current values before the update
                fetch_old_values_query = "SELECT POS, LOCATION, CONNECTED, NOTES, IMAGE FROM COMPONENTS WHERE `S/N` = :a;"
                old_values = conn.query(fetch_old_values_query, params={"a": selected_component_serial})
                
                # Convert the image to bytes if it's uploaded
                if image_upload:
                    component_image_filename = process_and_save_image(image_upload, selected_component_serial)
                else:
                    component_image_filename = None

                # Update the data in the SQL database
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if notes == "None":
                    notes = None
                # Update the data in the SQL database
                update_query = text(f"UPDATE COMPONENTS SET POS = :a, LOCATION = :b, CONNECTED = :c, NOTES = :d, IMAGE = :e, `LAST EDIT` = :f WHERE `S/N` = :g;")
                 # Insert the old values into the HISTORY table
                insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS CONNECTION', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g, :h, :i, :j, :k);")
                with conn.session as session:
                    session.execute(update_query, {"a": pos, "b": location, "c": selected_connection_serial, "d": notes, "e": component_image_filename, "f": timestamp, "g": selected_component_serial})
                    session.execute(insert_history_query, {"a": timestamp, "b": selected_component_serial, "c": old_values.iat[0, 1], "d": old_values.iat[0, 2], "e": old_values.iat[0, 3], "f": old_values.iat[0, 4], "g": location, "h": selected_connection_serial, "i": notes, "j": component_image_filename, "k": "COMPONENT UPDATE"})
                    session.commit()

                st.success("Changes saved successfully!")

                # Refresh the data in the app
                refresh_data()
                

            except sqlite3.Error as e:
                st.error(f"Error updating data: {e}")
    else:
        st.write("Oops, no devices... Check your search terms or refresh data!")

with history:
    st.subheader('History')

    # Search bar for history lookup
    search_history = st.text_input("Search in History", "")

    # Fetch data from the HISTORY table
    history_data_query = "SELECT `CHANGE TIME`, `DEVICE S/N`, `PREVIOUS LOCATION`, `PREVIOUS FRIENDLY NAME`, `PREVIOUS CONNECTION`, `PREVIOUS NOTES`, `NEW LOCATION`, `NEW FRIENDLY NAME`, `NEW CONNECTION`, `NEW NOTES`, `CHANGE LOG` FROM HISTORY;"

    # Fetch all rows from the cursor
    df_history = conn.query(history_data_query)
    
    # Sort DataFrame by 'CHANGE TIME' column in descending order
    df_history['CHANGE TIME'] = pd.to_datetime(df_history['CHANGE TIME'])
    df_history = df_history.sort_values(by='CHANGE TIME', ascending=False)

    # Filter history data based on search input across all columns
    if search_history:
        filtered_history = df_history[df_history.apply(lambda row: any(row.astype(str).str.contains(search_history, case=False)), axis=1)]
        st.dataframe(filtered_history, use_container_width=True, hide_index=True)
    else:
        # Display all history data
        st.dataframe(df_history, use_container_width=True, hide_index=True, column_order=("CHANGE LOG","DEVICE S/N","PREVIOUS LOCATION","NEW LOCATION","PREVIOUS FRIENDLY NAME","NEW FRIENDLY NAME","PREVIOUS CONNECTION","NEW CONNECTION","PREVIOUS NOTES","NEW NOTES","CHANGE TIME"))