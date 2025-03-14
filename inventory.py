#Unfortunately, due to how streamlit works, you must only use single line comments
#Multiline comments are rendered as markdown in the program itself

# To do before launch:
# Change all image columns from BLOB format to text
# Add IS_STORAGE to locations table in db

import streamlit as st
import os
import sqlite3
import pandas as pd
import datetime
from io import BytesIO
import pandas as pd
from PIL import Image
from sqlalchemy import text
import exifread
from zipfile import ZipFile


date = datetime.datetime.now()
today = date.strftime("%Y-%m-%d")
df_devices = pd.DataFrame()
df_components = pd.DataFrame()
df_history = pd.DataFrame()

#This is the main page confix which also includes the about and the full update history!
st.set_page_config(page_title= "HC Hardware",
                   page_icon= "💻",
                   initial_sidebar_state="auto",
                   layout="wide",
                   menu_items={
                       'Get Help':None,
                       'Report a Bug':None,
                       "About":'''### [F&B Hardware Inventory v3.0.0](https://github.com/JAndrewGibson/inventory_management)   
POS tracking software by [Andrew Gibson](https://github.com/JAndrewGibson)

Last updated: 6/10/23
### New features:
- Change "Apply Location Changes to Selected Components" logic so that components are only updated when there is a legitimate change to location.
- - Implement logic to check if a location is a storage location for the overview screen
- - Implement a way to change whether a location is a storage location from the "Locations" tab.
- Remove the hardcoded storage locations and add a checkbox to the location creation which defines if it's a storage location or not
- Button to download all photos
- - Remove images tab


### Roadmap:
- A better way to deal with e-wasted devices. Have them be removed from the active device table, but also be able to un-archive them incase someone makes a mistake. I might have to remove the "e-waste" name and call it "archive".
- Bulk add/import - for accepting shipments of new devices
- Reworked overview screen
- - Add graphs showing distribution of POS type 
- - Add a button to the overview screen which will flag any potential issues
- - - Photo in database but not in images folder
- - - Device and it's components not in the same location
- - - Devices that have been more than 6 months without an update
- - - Assets without edit history (Devices that were input directly in the database)
- Remove hardcoded "pos options", which only allows for SpotOn, Tapin2, Toast and Mashgin


### Previous changes:

##### V3.0 (6/10/24)
- Finally implemented "Apply Location Changes to Selected Components"
- Changed how components and devices are identified in the dropdown boxes, including parentheses with their serial number. 
- Added functionality to break component connection
- Serial number lookup is now cached
- Fixed bug when reassigning a device or component to a location that currently does not have any devices.
- Increased image quality to full quality
- Added functionality for image history
  - You can only change an image once per day, if you do more than that, it will overwrite.
- Added a check for duplicate S/N so that it is a caught exception on all assets and asset-types!
- Changed user feedback
  - If you add an asset that is already there, a notification appears.
  - When a new asset is added, a success message appears at the top.
  - When an asset is updated, a notification appears.
  - When an exception is caught, a yellow warning box appears at the top.
  - When there is an error, a red box appears at the top.
- Changed almost every comment for the entire code - MORE READABILITY 😎

##### V2.0 (4/19/24)
- Images fully re-implemented from the ground up
  - All images are now stored in the folder itself for optimization
  - JPG, JPEG and PNG are all supported
  - Implemented exifread to fix mobile phone jank
  - Implemented new Images tab showing all the images in the database
- Added Locations tab with image support and metrics about each location
  - Images are now editable
  - And re-editable, with special logic to reduce screen bloat once images are added to each location by hiding the uploader in an expander.
- Added new reports and separated reports from actions on the sidebar
- Database template has been updated to reflect the change
- Fixed component selection - it is now independent from the device page entirely
- Added links in the about page as well as the overview and sidebar

##### V1.0 (3/4/24)
- Both all filtering dropdown boxes are multi-select boxes (finally)
- All of the database connections are now cached until the refresh button is selected
- Filtering no longer affects the editing dropdown fields
- New template for Github (including history and all new changes!)
- Removed the photos from the history table
- If notes are left blank, they now return a None-type object

##### V0.4 (2/13/24)
- Caching has now been added to speed up the user experience
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

#This is overwriting the default streamlit style
hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

#This is the title that appears at the top of the page, it has to be in markdown for superscript to work
st.markdown("""
<style>
.title-superscript {
    font-size: 50%;
    position: relative;
    top: -0.5em;
}
</style>
<h1>HC Hardware <span class="title-superscript">v3.0.0</span></h1> 
""", unsafe_allow_html=True)

#Setting up my database connections and image folder
database_file = "POSHardware.db"
absolute_path = os.path.dirname(__file__)
conn = st.connection(name="connection", type="sql", url="sqlite:///" + os.path.join(absolute_path, database_file))
images_path = os.path.join(absolute_path, "images")

#This function is for everytime an image is uploaded or changed, it controls the quality, metedata and format.
def process_and_save_image(image_upload, sn):
    images_folder = "images"
    timestamp = str(datetime.datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(images_folder, exist_ok=True)

    _, original_extension = os.path.splitext(image_upload.name)
    original_extension = original_extension.lower()
    image_path = os.path.join(images_folder, f"{sn}_{timestamp}.jpg")

    try:
        #Read image bytes into memory for EXIF processing
        image_bytes = image_upload.getvalue()  
        with BytesIO(image_bytes) as f:
            tags = exifread.process_file(f, details=False)

        #Check for EXIF Orientation tag
        if "Image Orientation" in tags:
            orientation = tags["Image Orientation"].printable
            if orientation == "Rotated 90 CW":
                image = Image.open(BytesIO(image_bytes)).rotate(270, expand=True)
            elif orientation == "Rotated 180 CW":
                image = Image.open(BytesIO(image_bytes)).rotate(180)
            elif orientation == "Rotated 270 CW":
                image = Image.open(BytesIO(image_bytes)).rotate(90, expand=True)
            else:  #Other orientations or no orientation tag
                image = Image.open(BytesIO(image_bytes))
        else:
            image = Image.open(BytesIO(image_bytes))

        if original_extension not in (".jpg", ".jpeg"):
            image = image.convert('RGB')

        image.save(image_path, format='JPEG', quality=100)
        return os.path.basename(image_path)

    except Exception as e:  #Catch any errors
        st.error(f"Error processing image: {e}")
        return None

#This function is called almost every single time that anything is updated or changed (or the refresh data button is pressed).
def refresh_data():
    st.cache_data.clear()

#This is all of the tables in my database and the function that calls them to be saved in the application cache
#It may need to be reworked in the future if the data becomes too big and the application slows as a result
@st.cache_data
def fetch_data(table_name):
    query = f"SELECT * FROM {table_name};"
    result = conn.query(query)
    return result
@st.cache_data
def get_serial_number(friendly_name):
    device_row = df_devices[df_devices['FRIENDLY NAME'] == friendly_name]
    if not device_row.empty:
        return device_row.iloc[0]['S/N']
    else:
        return None

df_devices = fetch_data("DEVICES").sort_values(by='LAST EDIT', ascending=False)
df_components = fetch_data("COMPONENTS").sort_values(by='LAST EDIT', ascending=False)
df_history = fetch_data("HISTORY")
df_locations = fetch_data("LOCATIONS")
df_device_types = fetch_data("DEVICE_TYPES")
df_component_types = fetch_data("COMPONENT_TYPES")




#Sidebar Menu
#In this section I define all of the existing assets and asset-types so that I can check that we're not adding duplicates
#Then we have each form and it's corresponding function for updating the database
st.sidebar.title("Actions")

if st.sidebar.button("Refresh data"):
    refresh_data()

existing_locations = list(df_locations['LOCATION'].unique())
existing_devices = [name for name in df_devices['FRIENDLY NAME'].unique() if name is not None and name.strip() != ""]
existing_device_sn = [name for name in df_devices['S/N'].unique() if name is not None and name.strip() != ""]
existing_component_sn = [name for name in df_components['S/N'].unique() if name is not None and name.strip() != ""]
existing_device_types = list(df_device_types['DEVICE_TYPE'].unique())
existing_component_types = list(df_component_types['COMPONENT_TYPE'].unique())

#All of the forms
with st.sidebar.expander("**Add Device**"):
    with st.form("Add New Device"):
        pos_options = ["SpotOn", "Tapin2", "Toast", "Mashgin", "None"]
        device_pos = st.selectbox("POS", [""] + pos_options)
        device_sn = st.text_input("S/N (Serial Number)", "", key="device_sn")
        device_location = st.selectbox("Location", [""] + existing_locations)
        device_type = st.selectbox("Type", [""] + existing_device_types)
        device_friendly_name = st.text_input("Friendly Name", "")
        add_device_notes = st.text_input("Notes", "None")

        #File upload for new device image
        device_image_upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])

        #Submit button
        add_device_submit = st.form_submit_button("Add Device")

with st.sidebar.expander("**Add Component**"):
    with st.form("Add New Component"):
        pos_options = ["SpotOn", "Tapin2", "Toast", "Mashgin", "None"]
        component_pos = st.selectbox("POS", [""] + pos_options)
        component_sn = st.text_input("S/N (Serial Number)", "", key="component_sn")
        component_location = st.selectbox("Location", [""] + existing_locations)
        component_type = st.selectbox("Type", [""] + existing_component_types)
        component_connected = st.selectbox("Connected",[""] + existing_devices)
        add_component_notes = st.text_input("Notes", "None")

        #File upload for new component image
        component_image_upload = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])

        #Submit button
        add_component_submit = st.form_submit_button("Add Component")

with st.sidebar.expander("**Add Location**"):
    with st.form("Add New Location"):
        location_name = st.text_input("Location Name", "")
        storage_check = st.checkbox("This is a storage location.", value= False)

        #File upload for new location image
        location_image_upload = st.file_uploader("Upload a photo for the Image", type=["jpg", "jpeg", "png"])
        
        if location_image_upload:
            st.image(location_image_upload)

        #Submit button
        add_location_submit = st.form_submit_button("Add Location")
        
with st.sidebar.expander("**Add Device Type**"):
    with st.form("Add New Device Type"):
        device_type_name = st.text_input("Device Type Name", "")

        #File upload for new device type image
        device_type_image_upload = st.file_uploader("Upload a photo for the image", type=["jpg", "jpeg", "png"])
        
        if device_type_image_upload:
            st.image(device_type_image_upload)

        #Submit button
        add_device_type_submit = st.form_submit_button("Add Device Type")
        
with st.sidebar.expander("**Add Component Type**"):
    with st.form("Add New Component Type"):
        component_type_name = st.text_input("Component Type Name", "")

        #File upload for new component type image
        component_type_image_upload = st.file_uploader("Upload a photo for the image", type=["jpg", "jpeg", "png"])
        
        if component_type_image_upload:
            st.image(component_type_image_upload)

        #Submit button
        add_component_type_submit = st.form_submit_button("Add Component Type")

#All of the functions for submitting sidebar form data
if add_device_submit:
    #Validate and process the form data
    if device_sn and device_pos and device_location and device_type and not (device_sn in existing_device_sn):
        if add_device_notes == "None" or "":
            add_device_notes = None

        try:
            if device_image_upload:
                device_image_filename = process_and_save_image(device_image_upload, device_sn)
            else:
                device_image_filename = None

            #Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_query = text("INSERT INTO DEVICES (`S/N`, POS, LOCATION, `TYPE`, `FRIENDLY NAME`, NOTES, IMAGE, `LAST EDIT`) VALUES (:a, :b, :c, :d, :e, :f, :g, :h);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g);")
            with conn.session as session:
                session.execute(insert_query, {"a": device_sn, "b": device_pos, "c": device_location, "d": device_type, "e": device_friendly_name, "f": add_device_notes, "g": device_image_filename, "h": timestamp})
                session.execute(insert_history_query, {"a": timestamp, "b": device_sn, "c": device_location, "d": device_friendly_name, "e": add_device_notes, "f": device_image_filename, "g": "NEW DEVICE"})
                session.commit()
            st.success(f"A new {device_type} ({device_friendly_name}) was added successfully to {device_location}!")
            refresh_data()

        except sqlite3.IntegrityError as e:
            st.error(f"Error adding new device: {e}")
            
    elif device_sn in existing_device_sn:
        st.toast(f"Uh oh! Looks like {device_sn} already exists." , icon="🤔")
        st.toast("Try searching for it on the device page.", icon="🥹")
    else:
        st.warning(f"Make sure to include an S/N, POS, Location and Device Type!")
        
if add_component_submit:
    #Validate and process the form data
    if component_sn and component_pos and component_location and component_type and not (component_sn in existing_component_sn):
        if add_component_notes == "None" or "":
            add_component_notes = None
        try:
            if component_image_upload:
                component_image_filename = process_and_save_image(component_image_upload, component_sn)
            else:
                component_image_filename = None

            #Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_query = text("INSERT INTO COMPONENTS (POS, `TYPE`, `S/N`, LOCATION, CONNECTED, NOTES, IMAGE, `LAST EDIT`) VALUES (:a, :b, :c, :d, :e, :f, :g, :h);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g);")

            #Execute the query
            with conn.session as session:
                session.execute(insert_query, {"a": component_pos, "b": component_type, "c": component_sn, "d": component_location, "e": get_serial_number(component_connected), "f": add_component_notes, "g": component_image_filename, "h": timestamp})
                session.execute(insert_history_query, {"a": timestamp, "b": component_sn, "c": component_location, "d": get_serial_number(component_connected), "e": add_component_notes, "f": component_image_filename, "g": "NEW COMPONENT"})
                session.commit()
                        
            st.success(f"A new {component_type} ({component_sn}) was added successfully to {component_location}!")

            #Refresh the data in the app
            print("New Component Added")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.error(f"Error adding new component: {e}")
    elif component_sn in existing_component_sn:
        st.toast(f"{component_sn} is already in the db...", icon="😅")
        st.toast("Try searching for it on the component page!", icon="🙄")
    else:
        st.warning("Please fill out all required fields for component entry (S/N, POS, Location and Type).")

if add_location_submit:
    #Validate and process the form data
    if location_name and location_name not in existing_locations:
        try:
            if location_image_upload:
                location_image_filename = process_and_save_image(location_image_upload, location_name)
            else:
                location_image_filename = None

            #Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            #Execute the query
            insert_query = text("INSERT INTO LOCATIONS (LOCATION, IMAGE, IS_STORAGE) VALUES (:a, :b, :c);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW LOCATION', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d);")

            with conn.session as session:
                session.execute(insert_query, {"a": location_name, "b": location_image_filename, "c": storage_check})
                if storage_check == False:  
                    session.execute(insert_history_query, {"a": timestamp, "b": location_name, "c": location_image_filename, "d": "NEW LOCATION"})
                    session.commit()
                else:
                    session.execute(insert_history_query, {"a": timestamp, "b": location_name, "c": location_image_filename, "d": "NEW STORAGE LOCATION"})
                    session.commit()

            st.success(f"{location_name} has been created as a new location!")

            #Refresh the data in the app
            print("New Location Added")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new location: {e}")
    elif location_name in existing_locations:
        st.toast(f"{location_name} is already a location!", icon="🔥")
    else:
        st.warning("Please name your location.")
        
if add_device_type_submit:
    #Validate and process the form data
    if device_type_name and device_type_name not in existing_device_types:
        try:
            if device_type_image_upload:
                device_type_image_filename = process_and_save_image(device_type_image_upload, device_type_name)
            else:
                device_type_image_filename = None

            #Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            #Execute the query
            insert_query = text("INSERT INTO 'DEVICE_TYPES' (DEVICE_TYPE, IMAGE) VALUES (:a, :b);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c);")
            change_log_text = f"NEW DEVICE TYPE: {device_type_name}"

            
            with conn.session as session:
                session.execute(insert_query, {"a": device_type_name, "b": device_type_image_filename})
                session.execute(insert_history_query, {"a": timestamp, "b": device_type_image_filename, "c": change_log_text})
                session.commit()

            st.success(f"{device_type_name} has been created as a new device type!")

            #Refresh the data in the app
            print("New Device Type Added!")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new device type: {e}")
    elif device_type_name in existing_device_types:
        st.toast(f"What are you doing? {device_type} is already a device.", icon="🤷")
    else:
        st.warning("Please enter the type of device you need to record.")
        
if add_component_type_submit:
    #Validate and process the form data
    if component_type_name and component_type_name not in existing_component_types:
        try:
            if component_type_image_upload:
                component_type_image_filename = process_and_save_image(component_type_image_upload, component_type_name)
            else:
                component_type_image_filename = None


            #Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            #Execute the query
            insert_query = text("INSERT INTO 'COMPONENT_TYPES' (COMPONENT_TYPE, IMAGE) VALUES (:a, :b);")
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c);")
            change_log_text = f"NEW COMPONENT TYPE: {component_type_name}"

            
            with conn.session as session:
                session.execute(insert_query, {"a": component_type_name, "b": component_type_image_filename})
                session.execute(insert_history_query, {"a": timestamp, "b": component_type_image_filename, "c": change_log_text})
                session.commit()

            st.success(f"{component_type_name} has been created as a new component type!")

            #Refresh the data in the app
            print("New Component Type Added!")
            print("Beginning Data Refresh")
            refresh_data()

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new component type: {e}")
    elif component_type_name in existing_component_types:
        st.toast(f"I literally just saw {component_type_name} on the components page", icon="🤔")
    else:
        st.warning("Please enter the type of component you need to record.")


#I was told by some people to put this here, it's true.
#Although I do use this software for work because it makes my job easier, I made it for myself (it was previously just an excel sheet named: "RELATIONAL DATABASE") 🥹 
st.sidebar.markdown("##### [This software was created independently by Andrew Gibson outside of work hours.](https://github.com/JAndrewGibson/inventory_management)")

#This function is called when "Apply location changes to the connected components" check box is selected and the data is input.
#It loops over all of the connected components in the db and updates their location.
def apply_connected_changes(selected_device_serial):
    #Query to return a list of connected component's serial numbers
    connected_components_to_change = df_components[df_components['CONNECTED'] == selected_device_serial]['S/N'].unique()
    for serial in connected_components_to_change:
        try:
            #Fetch the current values before the update
            fetch_old_values_query = "SELECT POS, LOCATION, CONNECTED, NOTES, IMAGE FROM COMPONENTS WHERE `S/N` = :a;"
            old_values = conn.query(fetch_old_values_query, params={"a": serial})
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            #Update the data in the SQL database
            update_query = text(f"UPDATE COMPONENTS SET LOCATION = :a, `LAST EDIT` = :b WHERE `S/N` = :c;")
                #Insert the old values into the HISTORY table
            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS CONNECTION', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g, :h, :i, :j, :k);")
            with conn.session as session:
                session.execute(update_query, {"a": location, "b": timestamp, "c": serial})
                session.execute(insert_history_query, {"a": timestamp, "b": serial, "c": old_values.iat[0, 1], "d": old_values.iat[0, 2], "e": old_values.iat[0, 3], "f": old_values.iat[0, 4], "g": location, "h": old_values.iat[0, 2], "i": old_values.iat[0, 3], "j":  old_values.iat[0, 4], "k": "COMPONENT UPDATE FROM CONNECTED DEVICE"})
                session.commit()
        except sqlite3.Error as e:
                st.error(f"Error updating data: {e}")

    st.toast(f"Connected components ({connected_components_to_change}) saved successfully!", icon="🙌")
    

#This defines each of my tabs at the top of the screen
overview, devices, components, locations, history, reports = st.columns(6)
overview, devices, components, locations, history, reports = st.tabs(["Overview", "Devices", "Components", "Locations", "History", "Reports"])

#The next six 'with' statements are for each of the tabs and their functions. 

with overview:
    col1, col2 = st.columns(2)
    col1.subheader('Overview')
    
    #This is my counter logic and rephrasing for how many changes in the last 24 hours
    df_history['CHANGE TIME'] = pd.to_datetime(df_history['CHANGE TIME'])
    twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
    changes_last_24_hours = df_history[df_history['CHANGE TIME'] >= twenty_four_hours_ago].shape[0]
    if changes_last_24_hours == 1:
        changes_sentence = "There has only been one change"
    elif changes_last_24_hours > 1:
        changes_sentence = f"There have been {changes_last_24_hours} changes"
    else:
        changes_sentence = "Looking good! There have not been any changes"
    
    #Defining all of my device counts
    #This needs to be changed in the future to remove the hardcoded 'storage' locations
    total_devices = df_devices["S/N"].count()
    total_components = df_components["S/N"].count()
    wasted_devices = df_devices[df_devices['LOCATION'] == 'E-WASTED']['LOCATION'].count()
    wasted_components = df_components[df_components['LOCATION'] == 'E-WASTED']['LOCATION'].count()
    devices_without_photo = df_devices['IMAGE'].isnull().sum()
    components_without_photo = df_components['IMAGE'].isnull().sum()
    storage_locations = df_locations[df_locations['IS_STORAGE'] == True]['LOCATION'].tolist()
    devices_in_storage = df_devices[df_devices['LOCATION'].isin(storage_locations)]
    components_in_storage = df_components[df_components['LOCATION'].isin(storage_locations)]
    stored_assets = devices_in_storage.shape[0] + components_in_storage.shape[0]
    unknown_assets = df_devices[df_devices['LOCATION'] == 'UNKNOWN']['LOCATION'].count() + (df_components[df_components['LOCATION'] == 'UNKNOWN']['LOCATION'].count())    
        
    #Display the overview paragraph
    col1.write(f'''
            {changes_sentence} to the database in the last 24 hours.
            
            Right now there are {total_devices-wasted_devices} active devices and {total_components-wasted_components} components.
            {stored_assets} assets are currently in storage, {unknown_assets} are in an unknown location, and {wasted_devices + wasted_components} assets have been sent to E-Waste.
            
            There are {devices_without_photo} devices without a photo and {components_without_photo} components without a photo.
            
            Got ideas for what should be displayed on this page? [Tell Andrew!](https://github.com/JAndrewGibson)
            ''')

with devices:
    #Two columns for this page as well!
    col1, col2 = st.columns(2)
    col1.subheader('Devices')
   
    device_locations_list = ['All'] + list(existing_locations)
    selected_device_locations = col1.multiselect("Select a location", device_locations_list, default=["All"])
    device_type_list = ['All'] + list(existing_device_types)
    selected_types = col1.multiselect("Select a type", device_type_list, default=["All"])
    
    #This is the search bar for the table below
    search_device = col1.text_input("Search for a device", "")

    #Filtering logic for filtering the table by location, device type and search term
    #All is selected by default
    filtered_devices = df_devices.copy()
    if "All" not in selected_device_locations:
        filtered_devices = filtered_devices[filtered_devices['LOCATION'].isin(selected_device_locations)]
    if "All" not in selected_types:
        filtered_devices = filtered_devices[filtered_devices['TYPE'].isin(selected_types)]
    if search_device:
        filtered_devices = filtered_devices[filtered_devices.apply(lambda row: any(row.astype(str).str.contains(search_device, case=False)), axis=1)]

    #The Dataframe display for the filtered results
    if not filtered_devices.empty:
        col1.dataframe(filtered_devices, use_container_width=True, hide_index=True, column_order=("POS", "TYPE", "LOCATION","FRIENDLY NAME", "NOTES", "S/N","LAST EDIT"))
    
        #Here is the second column for actually editing the device
        col2.subheader('Edit Device')
        #Dropdown to select a device from the filtered list
        available_devices = filtered_devices.apply(
        lambda row: f"{row['FRIENDLY NAME']} at {row['LOCATION']} ({row['S/N']})",axis=1).tolist()
        #Create a mapping between display names and serial numbers
        display_name_to_serial = {display_name: serial for display_name, serial in zip(available_devices, filtered_devices['S/N'].tolist())}

        #Dropdown to select a device from the filtered list
        selected_device_display = col2.selectbox("Select a device to edit", available_devices)

        #Get the corresponding serial number based on the displayed name
        selected_device_serial = display_name_to_serial.get(selected_device_display, None)

        connected_components = df_components[df_components['CONNECTED'] == selected_device_serial]['TYPE'].unique()
        connected_components_text = " ".join(f'<span style="color:green">•</span> {component}' for component in connected_components)
        col2.markdown(connected_components_text, unsafe_allow_html=True)
        
        #Display editable fields
        if not filtered_devices.empty:
            print("Filtering Devices...")
            selected_device_index = filtered_devices[filtered_devices['S/N'] == selected_device_serial].index[0]

            #Editable Fields            
            pos_options = df_devices['POS'].unique()
            pos = col2.selectbox("Device POS", pos_options, index=pos_options.tolist().index(filtered_devices.at[selected_device_index, 'POS']))
            location_options = df_locations['LOCATION'].unique()
            location = col2.selectbox("Device Location", location_options, index=location_options.tolist().index(filtered_devices.at[selected_device_index, 'LOCATION']))
            save_changes_to_connected = col2.checkbox("Apply location changes to the connected components", value=False, label_visibility="visible")
            friendly_name = col2.text_input("Friendly Name", filtered_devices.at[selected_device_index, 'FRIENDLY NAME'])
            notes = col2.text_input("Device Notes", filtered_devices.at[selected_device_index, 'NOTES'])
            #Display existing image if available
            if 'IMAGE' in filtered_devices.columns:
                existing_image_filename = filtered_devices.at[selected_device_index, 'IMAGE']
                if existing_image_filename:
                    images_folder = "images" 
                    full_image_path = os.path.join(images_folder, existing_image_filename)

                    if os.path.exists(full_image_path):
                        with Image.open(full_image_path) as image:
                            col2.image(image, width=200)
                    else:
                        col2.warning("Image filename found in database but the file itself was not found. It may have been deleted.")
                        
            #File upload for image in the right column
            device_image_upload = None
            device_image_upload = col2.file_uploader("Upload a new photo?", type=["jpg", "jpeg", "png"])

            if col2.button("Save Device"):
                try:
                    #Fetch the current values before the update
                    fetch_old_values_query = "SELECT POS, LOCATION, `FRIENDLY NAME`, NOTES, IMAGE FROM DEVICES WHERE `S/N` = :a;"
                    old_values = conn.query(fetch_old_values_query, params={"a": selected_device_serial})
                    
                    if save_changes_to_connected == True and location != old_values.iat[0, 1]:
                        apply_connected_changes(selected_device_serial)
                    
                    if notes == "None":
                        notes = None
                    if friendly_name == "None":
                        friendly_name = None
                    
                    if device_image_upload:
                        device_image_filename = process_and_save_image(device_image_upload, selected_device_serial)
                    else:
                        device_image_filename = None
                    
                    #Update the data in the SQL database
                    update_query = text(f"UPDATE DEVICES SET POS = :a, LOCATION = :b, `FRIENDLY NAME` = :c, NOTES = :d, IMAGE = :e, `LAST EDIT` = :f WHERE `S/N` = :g;")
                    insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS FRIENDLY NAME', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW NOTES', 'NEW PHOTO','CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g, :h, :i, :j, :k);")
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with conn.session as session:
                        session.execute(update_query, {"a": pos, "b": location, "c": friendly_name, "d": notes, "e": device_image_filename, "f": timestamp, "g": selected_device_serial})
                        session.execute(insert_history_query, {"a": timestamp, "b": selected_device_serial, "c": old_values.iat[0, 1], "d": old_values.iat[0, 2], "e": old_values.iat[0, 3], "f": old_values.iat[0, 4], "g": location, "h": friendly_name, "i": notes, "j": device_image_filename, "k": "DEVICE UPDATE"})
                        session.commit()
                    
                    st.toast(f"Device {friendly_name} ({selected_device_serial}) updated successfully!", icon="🥳")
                    print("Changes saved successfully!")
                    #Refresh the data in the app
                    refresh_data()

                except sqlite3.Error as e:
                    st.error(f"Error updating data: {e}")
    else:
        col1.write("Oops, no devices... Check your search terms or refresh data!")
            
with components:
    #Everything has two columns
    col1, col2 = st.columns(2)
    col1.subheader('Components')
   
    component_locations_list = ['All'] + list(existing_locations)
    selected_component_locations = col1.multiselect("Select a location", component_locations_list, default=['All'], key="component_location_select")
    component_type_list = ['All'] + list(df_components['TYPE'].unique())
    selected_list = col1.multiselect("Select a type", component_type_list, default=['All'], key="component_type_select")
    search_components = col1.text_input("Search for a component", "")

    #Filter components based on search input and selected location
    if 'All' in selected_component_locations:
        filtered_components = df_components  #Show all components for now
        if 'All' not in selected_list:
            filtered_components = filtered_components[filtered_components['TYPE'].isin(selected_list)]
    else:
        filtered_components = df_components[df_components['LOCATION'].isin(selected_component_locations)]

    #Apply type filtering regardless of location selection (if 'All' types not selected)
    if 'All' not in selected_list:
        filtered_components = filtered_components[filtered_components['TYPE'].isin(selected_list)]

    if search_components:
        filtered_components = filtered_components[filtered_components.apply(lambda row: any(row.astype(str).str.contains(search_components, case=False)), axis=1)]


    #Display filtered components in a DataFrame
    col1.dataframe(filtered_components, use_container_width=True, hide_index=True, column_order=("POS", "TYPE", "LOCATION", "CONNECTED", "NOTES", "S/N","LAST EDIT"))
    
    col2.subheader('Edit Component')
    #Dropdown to select a component from the filtered list
    available_components = []
    if not filtered_components.empty:  #Check if DataFrame is not empty
        available_components = filtered_components.apply(lambda row: f"{row['TYPE']} at {row['LOCATION']} ({row['S/N']})", axis=1).tolist()
    #Create a mapping between display names and serial numbers
    display_name_to_serial = {display_name: serial for display_name, serial in zip(available_components, filtered_components['S/N'].tolist())}
    serial_to_display_name = {serial: display_name for serial, display_name in zip(available_components, filtered_components['S/N'].tolist())}

    #Dropdown to select a component from the filtered list
    selected_component_display = col2.selectbox("Select a component to edit", available_components)
    friendly_name_to_serial = df_devices.set_index('FRIENDLY NAME')['S/N'].to_dict()
    #Get the corresponding serial number based on the displayed name
    selected_component_serial = display_name_to_serial.get(selected_component_display, None)

    #Display editable fields
    if not filtered_components.empty:
        print("Filtering Components...")
        selected_component_index = filtered_components[filtered_components['S/N'] == selected_component_serial].index[0]

        #Add editable fields to the left column
        pos_options = df_components['POS'].unique()
        pos = col2.selectbox("Component POS", pos_options, index=pos_options.tolist().index(filtered_components.at[selected_component_index, 'POS']))
        location_options = df_locations['LOCATION'].unique()
        location = col2.selectbox("Component Location", location_options, index=location_options.tolist().index(filtered_components.at[selected_component_index, 'LOCATION']))
        
        #Get current component connection
        current_connection_serial = filtered_components.at[selected_component_index, 'CONNECTED']
        current_connection = df_devices[df_devices['S/N'] == current_connection_serial]['FRIENDLY NAME'].iloc[0] if current_connection_serial else None
        connection_options = (df_devices['FRIENDLY NAME'].unique())
        default_connection_index = connection_options.tolist().index(current_connection) if current_connection in connection_options else None
        connection = col2.selectbox("Component Connection", connection_options, index=default_connection_index)
        break_connection_box = col2.checkbox("Break connection", value=False,)
        component_notes = col2.text_input("Component Notes", filtered_components.at[selected_component_index, 'NOTES'])
        #Display existing image if available
        
        if 'IMAGE' in filtered_components.columns:
                existing_image_filename = filtered_components.at[selected_component_index, 'IMAGE']
                if existing_image_filename:
                    images_folder = "images" 
                    full_image_path = os.path.join(images_folder, existing_image_filename)

                    if os.path.exists(full_image_path):
                        with Image.open(full_image_path) as image:
                            col2.image(image, width=200) 
                    else:
                        col2.warning("Image filename found in database but the file itself was not found. It may have been deleted.")
                
        #File upload for image in the right column
        image_upload = None
        image_upload = col2.file_uploader("Upload a photo?", type=["jpg", "jpeg", "png"])
        if break_connection_box == True:
            selected_connection_serial = None
        else:
            selected_connection_serial = friendly_name_to_serial.get(connection)
        if col2.button("Save Component"):
            try:
                #Fetch the current values before the update
                fetch_old_values_query = "SELECT POS, LOCATION, CONNECTED, NOTES, IMAGE FROM COMPONENTS WHERE `S/N` = :a;"
                old_values = conn.query(fetch_old_values_query, params={"a": selected_component_serial})
                
                #Convert the image to bytes if it's uploaded
                if image_upload:
                    component_image_filename = process_and_save_image(image_upload, selected_component_serial)
                else:
                    component_image_filename = None

                #Update the data in the SQL database
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if component_notes == "None":
                    component_notes = None
                #Update the data in the SQL database
                update_query = text(f"UPDATE COMPONENTS SET POS = :a, LOCATION = :b, CONNECTED = :c, NOTES = :d, IMAGE = :e, `LAST EDIT` = :f WHERE `S/N` = :g;")
                 #Insert the old values into the HISTORY table
                insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS CONNECTION', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d, :e, :f, :g, :h, :i, :j, :k);")
                with conn.session as session:
                    session.execute(update_query, {"a": pos, "b": location, "c": selected_connection_serial, "d": component_notes, "e": component_image_filename, "f": timestamp, "g": selected_component_serial})
                    session.execute(insert_history_query, {"a": timestamp, "b": selected_component_serial, "c": old_values.iat[0, 1], "d": old_values.iat[0, 2], "e": old_values.iat[0, 3], "f": old_values.iat[0, 4], "g": location, "h": selected_connection_serial, "i": notes, "j": component_image_filename, "k": "COMPONENT UPDATE"})
                    session.commit()

                st.toast(f"Component ({selected_component_serial}) saved successfully!", icon="🙌")

                #Refresh the data in the app
                refresh_data()
                

            except sqlite3.Error as e:
                st.error(f"Error updating data: {e}")
    else:
        st.write("Oops, no devices... Check your search terms or refresh data!")

with locations:
    st.subheader("Locations")
    cols = st.columns(4) #Adjust the number of columns as needed
    for index, row in df_locations.iterrows():
        location_name = row["LOCATION"]
        image_filename = row["IMAGE"]
        is_storage = row["IS_STORAGE"]

        with cols[index % len(cols)]:
            with st.container():
                st.subheader(location_name)
                st.write(f'''
Devices: {df_devices[df_devices['LOCATION'] == location_name]['LOCATION'].count()}

Components: {df_components[df_components['LOCATION'] == location_name]['LOCATION'].count()}''')
                
                if st.checkbox("Storage location", value = is_storage,key=f"storage_{location_name}"):
                    is_now_storage = True
                else:
                    is_now_storage = False
                
                if image_filename:
                    images_folder = "images" 
                    image_path = os.path.join(images_folder, image_filename)
                    if os.path.exists(image_path):
                        st.image(image_path, width=200)
                    else:
                        st.warning("An image is listed for this location, but no file was found.")
                    with st.expander(f"Edit {location_name} photo"):
                        location_image_upload = st.file_uploader(f"Edit {location_name} photo", type=["jpg", "jpeg", "png"])
                        if st.button(f"Save {location_name}", f"{location_name}"):
                            location_image_filename = image_filename
                            if location_image_upload:
                                location_image_filename = process_and_save_image(location_image_upload, location_name)
                                if is_now_storage == is_storage:
                                        notes = f"{location_name} image updated!"   
                                elif is_now_storage == True:
                                    notes = f"{location_name} is now a storage location and it's image has been updated!"
                                else:
                                    notes = f"{location_name} is no longer a storage location and it's image has been updated!"
                            elif is_now_storage != is_storage and is_now_storage == True:
                                notes = f"{location_name} is now a storage location"
                            elif is_now_storage != is_storage and is_now_storage == False:
                                notes = f"{location_name} is no longer a storage location"
                            #Update the data in the SQL database
                            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            update_query = text(f"UPDATE LOCATIONS SET IMAGE = :a, IS_STORAGE = :b WHERE `LOCATION` = :c;")
                            insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d);")
                            with conn.session as session:
                                session.execute(update_query, {"a": location_image_filename, "b": is_now_storage, "c": location_name})
                                session.execute(insert_history_query, {"a": timestamp, "b": notes, "c": location_image_filename, "d": "LOCATION UPDATE"})
                                session.commit()
                                #Refresh the data in the app
                                refresh_data()
                                
                        
                else:
                    location_image_upload = st.file_uploader(f"There's no photo for {location_name}, why don't you add one?", type=["jpg", "jpeg", "png"])
                    if st.button(f"Save {location_name}", f"{location_name}"):
                        location_image_filename = image_filename
                        if location_image_upload:
                            location_image_filename = process_and_save_image(location_image_upload, location_name)
                            if is_now_storage == is_storage:
                                    notes = f"{location_name} image added!"   
                            elif is_now_storage == True:
                                notes = f"{location_name} is now a storage location and it's image has been added!"
                            else:
                                notes = f"{location_name} is no longer a storage location and it's image has been added!"
                        elif is_now_storage != is_storage and is_now_storage == True:
                            notes = f"{location_name} is now a storage location"
                        elif is_now_storage != is_storage and is_now_storage == False:
                            notes = f"{location_name} is no longer a storage location"
                        #Update the data in the SQL database
                        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        update_query = text(f"UPDATE LOCATIONS SET IMAGE = :a, IS_STORAGE = :b WHERE `LOCATION` = :c;")
                        insert_history_query = text("INSERT INTO HISTORY ('CHANGE TIME', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (:a, :b, :c, :d);")
                        with conn.session as session:
                            session.execute(update_query, {"a": location_image_filename, "b": is_now_storage, "c": location_name})
                            session.execute(insert_history_query, {"a": timestamp, "b": notes, "c": location_image_filename, "d": "LOCATION UPDATE"})
                            session.commit()
                            #Refresh the data in the app
                            refresh_data()
                                  
            st.divider()
                
with history:
    st.subheader('History')

    #Search bar for history lookup
    search_history = st.text_input("Search in History", "")

    #Fetch data from the HISTORY table
    history_data_query = "SELECT `CHANGE TIME`, `DEVICE S/N`, `PREVIOUS LOCATION`, `PREVIOUS FRIENDLY NAME`, `PREVIOUS CONNECTION`, `PREVIOUS NOTES`, `NEW LOCATION`, `NEW FRIENDLY NAME`, `NEW CONNECTION`, `NEW NOTES`, `CHANGE LOG` FROM HISTORY;"

    #Fetch all rows from the cursor
    df_history = conn.query(history_data_query)
    
    #Sort DataFrame by 'CHANGE TIME' column in descending order
    df_history['CHANGE TIME'] = pd.to_datetime(df_history['CHANGE TIME'])
    df_history = df_history.sort_values(by='CHANGE TIME', ascending=False)

    #Filter history data based on search input across all columns
    if search_history:
        filtered_history = df_history[df_history.apply(lambda row: any(row.astype(str).str.contains(search_history, case=False)), axis=1)]
        st.dataframe(filtered_history, use_container_width=True, hide_index=True)
    else:
        #Display all history data
        st.dataframe(df_history, use_container_width=True, hide_index=True, column_order=("CHANGE LOG","DEVICE S/N","PREVIOUS LOCATION","NEW LOCATION","PREVIOUS FRIENDLY NAME","NEW FRIENDLY NAME","PREVIOUS CONNECTION","NEW CONNECTION","PREVIOUS NOTES","NEW NOTES","CHANGE TIME"))


def download_full_report():
    #Read data from the DEVICES table into a DataFrame
    df_devices = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, `FRIENDLY NAME`, NOTES, `LAST EDIT` FROM DEVICES;")
    df_history = conn.query("SELECT `CHANGE TIME`, `DEVICE S/N`, `PREVIOUS LOCATION`, `PREVIOUS FRIENDLY NAME`, `PREVIOUS CONNECTION`, `PREVIOUS NOTES`, `NEW LOCATION`, `NEW FRIENDLY NAME`, `NEW CONNECTION`, `NEW NOTES` FROM HISTORY;")
    df_components = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, CONNECTED, NOTES, `LAST EDIT` FROM COMPONENTS;")
    print("Retreiving Full Report Data!")
    #Convert DataFrames to Excel with two sheets
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df_devices.to_excel(writer, sheet_name='DEVICES', index=False)
        df_components.to_excel(writer, sheet_name='COMPONENTS', index=False)
        df_history.to_excel(writer, sheet_name="HISTORY", index=False)

    #Save the Excel data to a BytesIO buffer
    excel_data.seek(0)
    return excel_data

def download_ewaste_report():
    #Read data from the DEVICES table into a DataFrame, filtering for E-WASTED
    df_devices = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, `FRIENDLY NAME`, NOTES, `LAST EDIT` FROM DEVICES WHERE LOCATION = 'E-WASTED';")
    df_history = conn.query("SELECT `CHANGE TIME`, `DEVICE S/N`, `PREVIOUS LOCATION`, `PREVIOUS FRIENDLY NAME`, `PREVIOUS CONNECTION`, `PREVIOUS NOTES`, `NEW LOCATION`, `NEW FRIENDLY NAME`, `NEW CONNECTION`, `NEW NOTES` FROM HISTORY WHERE `PREVIOUS LOCATION` = 'E-WASTED' OR `NEW LOCATION` = 'E-WASTED';")
    df_components = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, CONNECTED, NOTES, `LAST EDIT` FROM COMPONENTS WHERE LOCATION = 'E-WASTED';")

    print("Retreiving E-Waste Report Data!")
    #Convert DataFrames to Excel with two sheets
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df_devices.to_excel(writer, sheet_name='DEVICES', index=False)
        df_components.to_excel(writer, sheet_name='COMPONENTS', index=False)
        df_history.to_excel(writer, sheet_name="HISTORY", index=False)
        
    #Save the Excel data to a BytesIO buffer
    excel_data.seek(0)
    return excel_data

def download_active_report():
    df_devices = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, `FRIENDLY NAME`, NOTES, `LAST EDIT` FROM DEVICES WHERE LOCATION != 'E-WASTED';")
    df_history = conn.query("SELECT `CHANGE TIME`, `DEVICE S/N`, `PREVIOUS LOCATION`, `PREVIOUS FRIENDLY NAME`, `PREVIOUS CONNECTION`, `PREVIOUS NOTES`, `NEW LOCATION`, `NEW FRIENDLY NAME`, `NEW CONNECTION`, `NEW NOTES` FROM HISTORY WHERE `PREVIOUS LOCATION` != 'E-WASTED' AND `NEW LOCATION` != 'E-WASTED';")
    df_components = conn.query("SELECT POS, MODEL, TYPE, `S/N`, LOCATION, CONNECTED, NOTES, `LAST EDIT` FROM COMPONENTS WHERE LOCATION != 'E-WASTED';")

    print("Retreiving Data!")
    #Convert DataFrames to Excel with two sheets
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df_devices.to_excel(writer, sheet_name='DEVICES', index=False)
        df_components.to_excel(writer, sheet_name='COMPONENTS', index=False)
        df_history.to_excel(writer, sheet_name="HISTORY", index=False)
        
    #Save the Excel data to a BytesIO buffer
    excel_data.seek(0)
    return excel_data

def create_photo_zip_and_download_button(directory_path):
    photo_zip_filename = f"{today} POS IMAGES.zip"  # Name of the ZIP file
    with ZipFile(photo_zip_filename, "w") as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)  # Maintain original file names

    with open(photo_zip_filename, "rb") as f:
        photos_zip_bytes_data = f.read()

    return photos_zip_bytes_data
    
with reports:
    st.subheader("Reports")
        
    xlsx, csv, pdf, zip = st.columns(4)
    xlsx, csv, pdf, zip = st.tabs([".XLSX",".CSV", ".PDF", ".ZIP"])

    with xlsx:
        st.text("Select a button below to generate that report, a download button will appear once generated.")
        
        #Full Database Download Button
        if st.button(label="Full Database"):
            st.download_button(
                label="Full Database Download",
                data=download_full_report(),
                file_name=f"{today} POS Full Hardware Inventory.xlsx",
                key="download_full_report"
            )

        #E-Waste Devices Download button
        if st.button(label="E-Waste"):
            st.download_button(
                label="E-Waste Download",
                data=download_ewaste_report(),
                file_name=f"{today} POS E-Waste Report.xlsx",
                key="download_ewaste_report"
            )

        #Active Devices Download Button
        if st.button(label="Active Assets"):
            st.download_button(
                label="Active Assets Download",
                data=download_active_report(),
                file_name=f"{today} POS Active Report.xlsx",
                key="download_active_report"
            )
    
    
    with zip:
        if st.button(label="All POS Photos"):
            st.download_button(
                label="All POS photos download",
                data=create_photo_zip_and_download_button(images_path),
                file_name=f"{today} POS IMAGES.zip",
                key="download_photo_zip")
            
        if st.button("Create a .zip of EVERYTHING"):
            st.markdown('''Are you sure? This is EVERYTHING.
- The .db in it's entirety.
- All of the reports available
- Every photo ever uploaded here
- The complete history of every device
- The source code for this program
- The zip of the Github commits (meaning every other version of this software)

I just don't know why anyone would need that, but if you're sure - proceed.''',help='''
Seriously - there is no reason for you to download this right now aside from your curiosity.
You're just going to poke through it for a few minutes and then forget about it
And then what, you're just going to have it on your hard drive until you either get rid of the computer or re-install the OS

I'm just saying, what are you really accomplishing here?
''')
            with st.expander("Click here to proceed..."):
                st.markdown('''

Come on, please. Be serious. You do not need this file.
                            
Why would you? I don't even need this file and yet I'm still programming in this button, which is no small feat!

Whatever. Have it your way...
''')
                if st.button("Click here to generate the report that you DO NOT need."):
                    create_photo_zip_and_download_button(images_path)
                