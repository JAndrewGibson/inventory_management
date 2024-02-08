import streamlit as st
import os
import sqlite3
import pandas as pd
import datetime
import io
from io import BytesIO
import pandas as pd
from PIL import Image

absolute_path = os.path.dirname(__file__)

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
                       "About":'''# F&B HARDWARE INVENTORY   
### Version 0.9 
# Roadmap:
- Ability to use a checkbox to affect changes on the component when changing device.
- Making the location dropdowns into 'selectbox' attribute type on the component page.
- Create new template for Github!'''
                       })

hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

st.title("HC Hardware")

def download_excel():
    # Connect to the SQLite database
    conn = sqlite3.connect(os.path.join(absolute_path, 'POSHardware.db'))

    # Read data from the DEVICES table into a DataFrame
    df_devices = pd.read_sql_query("SELECT * FROM DEVICES;", conn)
    df_history = pd.read_sql_query("SELECT * FROM HISTORY;", conn)
    df_components = pd.read_sql_query("SELECT * FROM COMPONENTS;", conn)

    # Exclude the 'IMAGE' column from both DataFrames
    df_devices = df_devices.drop(columns=['IMAGE'])
    df_components = df_components.drop(columns=['IMAGE'])
    df_history = df_history.drop(columns=["PREVIOUS PHOTO","NEW PHOTO"])
    

    # Convert DataFrames to Excel with two sheets
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df_devices.to_excel(writer, sheet_name='DEVICES', index=False)
        df_components.to_excel(writer, sheet_name='COMPONENTS', index=False)
        df_history.to_excel(writer, sheet_name="HISTORY", index=False)

    # Save the Excel data to a BytesIO buffer
    excel_data.seek(0)

    # Close the connection
    conn.close()

    return excel_data

def fetch_data(cursor, table_name):
    query = f"SELECT * FROM {table_name};"
    result = cursor.execute(query).fetchall()
    return result

def load_data(table):
    # Connect to SQLite database
    conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
    cursor = conn.cursor()

    data = fetch_data(cursor, table)
    df = pd.DataFrame(data, columns=[col[0] for col in cursor.description])

    # Return both the DataFrame and the cursor
    return df

def get_serial_number(friendly_name):
    # Assuming df_devices is your DataFrame containing device information
    device_row = df_devices[df_devices['FRIENDLY NAME'] == friendly_name]
    if not device_row.empty:
        return device_row.iloc[0]['S/N']
    else:
        return None  # Handle case where no matching device is found

df_devices = load_data("DEVICES").sort_values(by='LAST EDIT', ascending=False)
df_components = load_data("COMPONENTS").sort_values(by='LAST EDIT', ascending=False)
df_history = load_data("HISTORY")
df_presets = load_data("PRESETS")

# Sidebar menu
st.sidebar.title("Actions")

if st.sidebar.button("Refresh data"):
    df_devices = load_data("DEVICES")
    df_components = load_data("COMPONENTS")
    df_history = load_data("HISTORY")
    
# Download the Excel file
st.sidebar.download_button(
    label="Download as Excel",
    data=download_excel(),
    file_name=f"{today} POS Hardware Inventory.xlsx",
    key="download_excel_button"
)

existing_locations = list(df_presets['LOCATION'].unique())
existing_device_types = list(df_devices['TYPE'].unique())
existing_component_types = list(df_components['TYPE'].unique())
existing_devices = [name for name in df_devices['FRIENDLY NAME'].unique() if name is not None and name.strip() != ""]

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
        device_image_upload = st.file_uploader("Upload a photo for the Image", type=["jpg", "jpeg", "png"])

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

        # File upload for new device image
        component_image_upload = st.file_uploader("Upload a photo for the Image", type=["jpg", "jpeg", "png"])

        # Submit button
        add_component_submit = st.form_submit_button("Add Component")

with st.sidebar.expander("**Add Location**"):
    with st.form("Add New Location"):
        location_name = st.text_input("Location Name", "")

        # File upload for new device image
        location_image_upload = st.file_uploader("Upload a photo for the Image", type=["jpg", "jpeg", "png"])
        
        if location_image_upload:
            st.image(location_image_upload)

        # Submit button
        add_location_submit = st.form_submit_button("Add Location")

# Process the form submission
if add_device_submit:
    # Validate and process the form data (you can add your logic here)
    if device_sn and device_pos and device_location and device_type:
        if device_notes == "None" or "":
            device_notes = None
        # Connect to the database and add the new device
        conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
        cursor = conn.cursor()

        try:
            # Convert the new image to bytes
            device_image_bytes = None
            if device_image_upload:
                device_image_bytes = device_image_upload.read()

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            insert_query = "INSERT INTO DEVICES (`S/N`, POS, LOCATION, `TYPE`, `FRIENDLY NAME`, NOTES, IMAGE, `LAST EDIT`) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            cursor.execute(insert_query, (device_sn, device_pos, device_location, device_type, device_friendly_name, device_notes, device_image_bytes, timestamp))

            # Insert the new values into the HISTORY table
            insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (?, ?, ?, ?, ?, ?, ?);"
            cursor.execute(insert_history_query, (timestamp, device_sn, device_location, device_friendly_name, device_notes, device_image_bytes, "NEW DEVICE"))

            # Commit the changes
            conn.commit()
            st.success("New device added successfully!")

            # Refresh the data in the app
            df_devices = load_data("DEVICES")
            df_components = load_data("COMPONENTS")
            df_history = load_data("HISTORY")

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new device: {e}")

        finally:
            # Close the connection
            conn.close()
    else:
        st.sidebar.warning("Please fill out all required fields for device entry (S/N, POS, Location and Type).")

if add_component_submit:
    # Validate and process the form data (you can add your logic here)
    if component_sn and component_pos and component_location and component_type:
        if component_notes == "None" or "":
            component_notes = None
        # Connect to the database and add the new device
        conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
        cursor = conn.cursor()

        try:
            # Insert the new component into the COMPONENT table
            insert_query = "INSERT INTO COMPONENTS (POS, `TYPE`, `S/N`, LOCATION, CONNECTED, NOTES, IMAGE, `LAST EDIT`) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
            
            # Convert the new image to bytes
            component_image_bytes = None
            if component_image_upload:
                component_image_bytes = component_image_upload.read()

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute the query
            cursor.execute(insert_query, (component_pos, component_type, component_sn, component_location, get_serial_number(component_connected), component_notes, component_image_bytes, timestamp))

            # Insert the new values into the HISTORY table
            insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (?, ?, ?, ?, ?, ?, ?);"
            cursor.execute(insert_history_query, (timestamp, component_sn, component_location, get_serial_number(component_connected), component_notes, component_image_bytes, "NEW COMPONENT"))

            # Commit the changes
            conn.commit()
            st.success("New component added successfully!")

            # Refresh the data in the app
            df_devices = load_data("DEVICES")
            df_components = load_data("COMPONENTS")
            df_history = load_data("HISTORY")

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new component: {e}")

        finally:
            # Close the connection
            conn.close()
    else:
        st.sidebar.warning("Please fill out all required fields for component entry (S/N, POS, Location and Type).")

if add_location_submit:
    # Validate and process the form data (you can add your logic here)
    if location_name:
        # Connect to the database and add the new device
        conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
        cursor = conn.cursor()

        try:
            # Convert the new image to bytes
            location_image_bytes = None
            if location_image_upload:
                location_image_bytes = Image.open(io.BytesIO(location_image_upload.read()))

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute the query
            insert_query = "INSERT INTO PRESETS (LOCATION, IMAGE) VALUES (?, ?);"
            cursor.execute(insert_query, (location_name, location_image_bytes))

            # Insert the new values into the HISTORY table
            insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'NEW LOCATION', 'NEW PHOTO', 'CHANGE LOG') VALUES (?, ?, ?, ?);"
            cursor.execute(insert_history_query, (timestamp, location_name, location_image_bytes, "NEW LOCATION"))

            # Commit the changes
            conn.commit()
            st.success("New location added successfully!")

            # Refresh the data in the app
            df_devices = load_data("DEVICES")
            df_components = load_data("COMPONENTS")
            df_history = load_data("HISTORY")
            df_presets = load_data("PRESETS")

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new location: {e}")

        finally:
            # Close the connection
            conn.close()
    else:
        st.sidebar.warning("Please name your location.")

overview, devices, components, history = st.columns(4)

overview, devices, components, history = st.tabs(["Overview", "Devices", "Components", "History"])

with overview:
    col1, col2 = st.columns(2)
    col1.subheader('Overview')
    
    # Count the number of changes in the last 24 hours
    df_history['CHANGE TIME'] = pd.to_datetime(df_history['CHANGE TIME'])
    twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
    changes_last_24_hours = df_history[df_history['CHANGE TIME'] >= twenty_four_hours_ago].shape[0]
    col1.write(f"Changes in the last 24 hours: {changes_last_24_hours}")
    
    # Count the number without a photo
    total_devices = df_devices["S/N"].count()
    total_components = df_components["S/N"].count()
    wasted_devices = df_devices[df_devices['LOCATION'] == 'E-WASTED']['LOCATION'].count()
    wasted_components = df_components[df_components['LOCATION'] == 'E-WASTED']['LOCATION'].count()
    devices_without_photo = df_devices['IMAGE'].isnull().sum()
    components_without_photo = df_components['IMAGE'].isnull().sum()
    stored_assets = df_devices[df_devices['LOCATION'] == 'WAREHOUSE']['LOCATION'].count() + (df_components[df_components['LOCATION'] == 'WAREHOUSE']['LOCATION'].count()) + (df_devices[df_devices['LOCATION'] == "JACK DANIEL'S OFFICE"]['LOCATION'].count()) + (df_components[df_components['LOCATION'] == "JACK DANIEL'S OFFICE"]['LOCATION'].count())
    unknown_assets = df_devices[df_devices['LOCATION'] == 'UNKNOWN']['LOCATION'].count() + (df_components[df_components['LOCATION'] == 'UNKNOWN']['LOCATION'].count())    
    

    # Display the counter
    col1.write(f'''
               Right now there are {total_devices-wasted_devices} active devices and {total_components-wasted_components} components.
               There are {devices_without_photo} devices and {components_without_photo} components that do not have a photo.
               {stored_assets} assets are currently in storage, {unknown_assets} are in an unknown location, and {wasted_devices + wasted_components} assets have been sent to E-Waste.
               There has been {changes_last_24_hours} change(s) to the database in the last 24 hours.
               
               Got ideas for what should be displayed on this page? Tell Andrew!
               ''')
    
    location_data = df_devices.groupby("LOCATION")["S/N"].nunique().reset_index()
    POS_data = df_devices.groupby("POS")["S/N"].nunique()
    
    # Display the data in a table
    col2.dataframe(location_data, hide_index=True, use_container_width=True,)
    col1.dataframe(POS_data)

with devices:
    col1, col2 = st.columns(2)
    col1.subheader('Devices')
   
    locations_list = ['All'] + list(existing_locations)
    selected_locations = col1.multiselect("Select a location", locations_list, default=["All"])
    type_list = ['All'] + list(df_devices['TYPE'].unique())
    selected_types = col1.multiselect("Select a type", type_list, default=["All"])
    # Search bar for device lookup
    search_device = col1.text_input("Search for a device", "")

    # Filter devices based on search input and selected location
    filtered_devices = df_devices.copy()
    if "All" not in selected_locations:
        filtered_devices = filtered_devices[filtered_devices['LOCATION'].isin(selected_locations)]
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
            selected_device_index = filtered_devices[filtered_devices['S/N'] == selected_device_serial].index[0]

            # Editable Fields
            pos_options = filtered_devices['POS'].unique()
            pos = col2.selectbox("Device POS", pos_options, index=pos_options.tolist().index(filtered_devices.at[selected_device_index, 'POS']))
            location_options = filtered_devices['LOCATION'].unique()
            location = col2.selectbox("Device Location", location_options, index=location_options.tolist().index(filtered_devices.at[selected_device_index, 'LOCATION']))
            friendly_name = col2.text_input("Friendly Name", filtered_devices.at[selected_device_index, 'FRIENDLY NAME'])
            notes = col2.text_input("Device Notes", filtered_devices.at[selected_device_index, 'NOTES'])
            # Display existing image if available
            if 'IMAGE' in filtered_devices.columns:
                existing_image = filtered_devices.at[selected_device_index, 'IMAGE']
                if existing_image:
                    col2.image(existing_image, width=200)
                        
            # File upload for image in the right column
            image_upload = None
            image_upload = col2.file_uploader("Upload a new photo?", type=["jpg", "jpeg", "png"])

            # Check if an image is uploaded
            if image_upload:
                uploaded_image = Image.open(io.BytesIO(image_upload.read()))
                target_size = (400, 400)
                resized_image = uploaded_image.resize(target_size)
                rotated_image = resized_image.rotate(270, expand=True)
                col2.image(rotated_image, caption="Uploaded Image", width=200)

            if col2.button("Save Device"):
                # Connect to the database
                conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
                cursor = conn.cursor()

                try:
                    # Fetch the current values before the update
                    fetch_old_values_query = "SELECT POS, LOCATION, `FRIENDLY NAME`, NOTES, IMAGE FROM DEVICES WHERE `S/N` = ?;"
                    old_values = cursor.execute(fetch_old_values_query, (selected_device_serial,)).fetchone()
                    
                    if notes == "None":
                        notes = None
                    if friendly_name == "None":
                        friendly_name = None
                    
                    # Convert the image to bytes if it's uploaded
                    image_bytes = image_upload.getvalue() if image_upload else old_values[4]
                    
                    # Update the data in the SQL database
                    update_query = f"UPDATE DEVICES SET POS = ?, LOCATION = ?, `FRIENDLY NAME` = ?, NOTES = ?, IMAGE = ?, `LAST EDIT` = ? WHERE `S/N` = ?;"
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute(update_query, (pos, location, friendly_name, notes, image_bytes, timestamp, selected_device_serial))

                    print("Image bytes before updating database:", image_bytes)

                    # Insert the old values into the HISTORY table
                    insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS FRIENDLY NAME', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW NOTES', 'NEW PHOTO','CHANGE LOG') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
                    cursor.execute(insert_history_query, (timestamp, selected_device_serial, old_values[1], old_values[2], old_values[3], old_values[4], location, friendly_name, notes, image_bytes, "DEVICE UPDATE"))

                    # Commit the changes
                    conn.commit()
                    st.success("Changes saved successfully!")

                    # Refresh the data in the app
                    df_devices = load_data("DEVICES")
                    df_components = load_data("COMPONENTS")
                    df_history = load_data("HISTORY")

                except sqlite3.Error as e:
                    st.error(f"Error updating data: {e}")

                finally:
                    conn.close()
    else:
        col1.write("Oops, no devices... Check your search terms or contact Andrew!")
            
with components:
    col1, col2 = st.columns(2)
    col1.subheader('Components')
   
    locations_list = ['All'] + list(existing_locations)
    selected_location = col1.selectbox("Select a location", locations_list) #I'd like to move this to a select box soon.
    type_list = ['All'] + list(df_components['TYPE'].unique())
    selected_list = col1.selectbox("Select a type", type_list)
    # Search bar for component lookup
    search_components = col1.text_input("Search for a component", "")

    # Filter components based on search input and selected location
    if selected_location == 'All':
        filtered_components = df_components
        if search_components:
            filtered_components = filtered_components[filtered_components.apply(lambda row: any(row.astype(str).str.contains(search_components, case=False)), axis=1)]
    else:
        filtered_components = df_components[df_components['LOCATION'] == selected_location]
        if search_components:
            filtered_components = filtered_components[filtered_components.apply(lambda row: any(row.astype(str).str.contains(search_components, case=False)), axis=1)]

    # Display filtered components in a DataFrame
    col1.dataframe(filtered_components, use_container_width=True, hide_index=True, column_order=("POS", "TYPE", "LOCATION", "CONNECTED", "NOTES", "S/N","LAST EDIT"))
      
    col2.subheader('Edit Component')
    # Dropdown to select a component from the filtered list
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
        selected_component_index = filtered_components[filtered_components['S/N'] == selected_component_serial].index[0]

        # Add editable fields to the left column
        pos_options = filtered_components['POS'].unique()
        pos = col2.selectbox("Component POS", pos_options, index=pos_options.tolist().index(filtered_components.at[selected_component_index, 'POS']))
        location_options = filtered_components['LOCATION'].unique()
        location = col2.selectbox("Component Location", location_options, index=location_options.tolist().index(filtered_components.at[selected_component_index, 'LOCATION']))
        connection_options = df_devices['FRIENDLY NAME'].unique()
        
        # Get current component connection
        current_connection_serial = filtered_components.at[selected_component_index, 'CONNECTED']
        current_connection = df_devices[df_devices['S/N'] == current_connection_serial]['FRIENDLY NAME'].iloc[0] if current_connection_serial else None
        connection_options = df_devices['FRIENDLY NAME'].unique()
        default_connection_index = connection_options.tolist().index(current_connection) if current_connection in connection_options else 0
        connection = col2.selectbox("Component Connection", connection_options, index=default_connection_index)
        notes = col2.text_input("Component Notes", filtered_components.at[selected_component_index, 'NOTES'])
        # Display existing image if available
        if 'IMAGE' in filtered_components.columns:
            existing_image = filtered_components.at[selected_component_index, 'IMAGE']
            if existing_image:
                col2.image(existing_image, width=200)
                
        # File upload for image in the right column
        image_upload = None
        image_upload = col2.file_uploader("Upload a photo?", type=["jpg", "jpeg", "png"])

        # Check if an image is uploaded
        if image_upload:
            uploaded_image = Image.open(io.BytesIO(image_upload.read()))
            col2.image(uploaded_image, width=200)

        
        selected_connection_serial = friendly_name_to_serial.get(connection)
        if col2.button("Save Component"):
            # Connect to the database
            conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
            cursor = conn.cursor()

            try:
                # Fetch the current values before the update
                fetch_old_values_query = "SELECT POS, LOCATION, CONNECTED, NOTES, IMAGE FROM COMPONENTS WHERE `S/N` = ?;"
                old_values = cursor.execute(fetch_old_values_query, (selected_component_serial,)).fetchone()
                
                # Convert the image to bytes if it's uploaded
                image_bytes = image_upload.getvalue() if image_upload else old_values[4]

                # Update the data in the SQL database
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if notes == "None":
                    notes = None
                # Update the data in the SQL database
                update_query = f"UPDATE COMPONENTS SET POS = ?, LOCATION = ?, CONNECTED = ?, NOTES = ?, IMAGE = ?, `LAST EDIT` = ? WHERE `S/N` = ?;"
                cursor.execute(update_query, (pos, location, selected_connection_serial, notes, image_bytes, timestamp, selected_component_serial))

                # Insert the old values into the HISTORY table
                insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS CONNECTION', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO', 'CHANGE LOG') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
                cursor.execute(insert_history_query, (timestamp, selected_component_serial, old_values[1], old_values[2], old_values[3], old_values[4], location, selected_connection_serial, notes, image_bytes, "COMPONENT UPDATE"))

                # Commit the changes
                conn.commit()
                st.success("Changes saved successfully!")

                # Refresh the data in the app
                df_devices = load_data("DEVICES")
                df_components = load_data("COMPONENTS")
                df_history = load_data("HISTORY")

            except sqlite3.Error as e:
                st.error(f"Error updating data: {e}")

            finally:
                conn.close()
    else:
        st.write("Oops, no devices...")

with history:
    st.subheader('History')

    # Search bar for history lookup
    search_history = st.text_input("Search in History", "")

    # Fetch data from the HISTORY table
    history_data_query = "SELECT * FROM HISTORY;"

    # Connect to the database
    conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
    cursor = conn.cursor()

    # Execute the history data query
    cursor.execute(history_data_query)

    # Fetch all rows from the cursor
    history_data = cursor.fetchall()

    # Create a DataFrame from the fetched data
    df_history = pd.DataFrame(history_data, columns=[col[0] for col in cursor.description])
    
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

    # Close the connection
    conn.close()
