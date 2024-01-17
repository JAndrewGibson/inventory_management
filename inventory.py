import streamlit as st
import os
import sqlite3
import pandas as pd
import datetime
import io
from io import BytesIO
import pandas as pd
import datetime
from PIL import Image

absolute_path = os.path.dirname(__file__)

today = datetime.date

df_current = pd.DataFrame()
df_history = pd.DataFrame()


st.set_page_config(page_title= "HC Hardware",
                   page_icon= "🔢",
                   initial_sidebar_state="auto",
                   layout="wide",
                   menu_items={
                       'Get Help':None,
                       'Report a Bug':None,
                       "About":'''# F&B REPORTING   
## Version 0.3
This is a custom solution made by Andrew Gibson for the visualization and configuration of all hardware inventory within the F&B department of the Honda Center.  
Not yet implemented:
- A list of all things not yet implemented'''
                       })


# Function to convert SQLite database to Excel and initiate download
def download_excel():
    # Connect to the SQLite database
    conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))

    # Read data from the database into a DataFrame
    df_current = pd.read_sql_query("SELECT * FROM CURRENT;", conn)

    # Exclude the 'IMAGE' column
    df_current = df_current.drop(columns=['IMAGE'])
    
    # Convert DataFrame to Excel
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df_current.to_excel(writer, sheet_name='POS HARDWARE', index=False)

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

# Load data
df_current = load_data("CURRENT")
df_history = load_data("HISTORY")

# Sidebar menu
st.sidebar.title("Add a device")

existing_locations = list(df_current['LOCATION'].unique())
existing_types = list(df_current['TYPE'].unique())
existing_devices = [name for name in df_current['FRIENDLY NAME'].unique() if name is not None and name.strip() != ""]

# Form to add a new device
with st.sidebar.form("Add New Device"):
    # Add form fields
    pos_options = ["SpotOn", "Tapin2", "Toast", "Mashgin"]
    new_pos = st.selectbox("POS", [""] + pos_options)
    new_sn = st.text_input("S/N (Serial Number)", "", key="new_sn")
    new_location = st.selectbox("Location", [""] + existing_locations)
    new_type = st.selectbox("Type", [""] + existing_types)
    new_friendly_name = st.text_input("Friendly Name", "")
    new_connected = st.selectbox("Connected",[""] + existing_devices)
    new_notes = st.text_input("Notes", "")

    # File upload for new device image
    new_image_upload = st.file_uploader("Upload a photo for the Image", type=["jpg", "jpeg", "png"])

    # Submit button
    add_device_submit = st.form_submit_button("Add Device")



# Process the form submission
if add_device_submit:
    # Validate and process the form data (you can add your logic here)
    if new_sn and new_pos and new_location and new_type and new_connected:
        # Connect to the database and add the new device
        conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
        cursor = conn.cursor()

        try:
            # Insert the new device into the CURRENT table
            insert_query = "INSERT INTO CURRENT (`S/N`, POS, LOCATION, `TYPE`, `FRIENDLY NAME`, CONNECTED, NOTES, IMAGE, `LAST EDIT`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"
            
            # Convert the new image to bytes
            new_image_bytes = None
            if new_image_upload:
                new_image_bytes = new_image_upload.read()

            # Get the current timestamp
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute the query
            cursor.execute(insert_query, (new_sn, new_pos, new_location, new_type, new_friendly_name, new_connected, new_notes, new_image_bytes, timestamp))

            # Insert the new values into the HISTORY table
            insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO') VALUES (?, ?, ?, ?, ?, ?, ?);"
            cursor.execute(insert_history_query, (timestamp, new_sn, new_location, new_friendly_name, new_connected, new_notes, new_image_bytes))

            # Commit the changes
            conn.commit()
            st.sidebar.success("New device added successfully!")

            # Refresh the data in the app
            df_current = load_data("CURRENT")
            df_history = load_data("HISTORY")

        except sqlite3.Error as e:
            st.sidebar.error(f"Error adding new device: {e}")

        finally:
            # Close the connection
            conn.close()
    else:
        st.sidebar.warning("Please fill out all required fields (S/N, POS, Location, Type, Connected).")
        



st.title("HC Hardware")

if st.button("Refresh data"):
    df_current = load_data("CURRENT")
    df_history = load_data("HISTORY")
    
# Download the Excel file
st.download_button(
    label="Download Excel",
    data=download_excel(),
    file_name=f"inventory_data.xlsx",
    key="download_excel_button"
)


overview, devices, history = st.columns(3)

overview, devices, history = st.tabs(["Overview", "Devices", "History"])

with overview:
    st.subheader('Breakdown by location')
    
    # Assuming 'CHANGE TIME' is the timestamp column in your DataFrame
    df_history['CHANGE TIME'] = pd.to_datetime(df_history['CHANGE TIME'])

    # Calculate the timestamp for 24 hours ago
    twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)

    # Count the number of changes in the last 24 hours
    changes_last_24_hours = df_history[df_history['CHANGE TIME'] >= twenty_four_hours_ago].shape[0]

    # Display the counter
    st.write(f"Changes in the last 24 hours: {changes_last_24_hours}")
    
    # Count the number of devices without a photo
    devices_without_photo = df_current['IMAGE'].isnull().sum()

    # Display the counter
    st.write(f"Devices without a photo: {devices_without_photo}")
    
    
    # Group data by "LOCATION" and count unique values in "CONNECTED" column
    grouped_data = df_current.groupby("LOCATION")["CONNECTED"].nunique().reset_index()
    
    # Display the data in a table
    st.dataframe(grouped_data, hide_index=True, use_container_width=True,)

    
with devices:
    st.subheader('Devices')
    
    locations_list = ['All'] + list(df_current['LOCATION'].unique())
    selected_location = st.selectbox("Select a location", locations_list)
    # Search bar for device lookup
    search_device = st.text_input("Search for a device", "")

    # Filter devices based on search input and selected location
    if selected_location == 'All':
        filtered_devices = df_current
        if search_device:
            filtered_devices = filtered_devices[filtered_devices.apply(lambda row: any(row.astype(str).str.contains(search_device, case=False)), axis=1)]
    else:
        filtered_devices = df_current[df_current['LOCATION'] == selected_location]
        if search_device:
            filtered_devices = filtered_devices[filtered_devices.apply(lambda row: any(row.astype(str).str.contains(search_device, case=False)), axis=1)]

    # Display filtered devices in a DataFrame
    st.dataframe(filtered_devices, use_container_width=True, hide_index=True, column_order=("POS", "TYPE", "LOCATION","FRIENDLY NAME","CONNECTED", "NOTES", "S/N","LAST EDIT"))
      
    st.subheader('Edit Device')
    # Dropdown to select a device from the filtered list
    available_devices = filtered_devices.apply(
    lambda row: row['FRIENDLY NAME'] if not pd.isnull(row['FRIENDLY NAME']) else f"{row['TYPE']} connected to {row['CONNECTED']}",
    axis=1
).tolist()
    # Create a mapping between display names and serial numbers
    display_name_to_serial = {display_name: serial for display_name, serial in zip(available_devices, filtered_devices['S/N'].tolist())}

    # Dropdown to select a device from the filtered list
    selected_device_display = st.selectbox("Select a device to edit", available_devices)

    # Get the corresponding serial number based on the displayed name
    selected_device_serial = display_name_to_serial.get(selected_device_display, None)

    # Display editable fields
    if not filtered_devices.empty:
        selected_device_index = filtered_devices[filtered_devices['S/N'] == selected_device_serial].index[0]

        # Create three columns
        col1, col2, col3 = st.columns(3)

        # Add editable fields to the left column
        pos_options = filtered_devices['POS'].unique()
        pos = col1.selectbox("POS", pos_options, index=pos_options.tolist().index(filtered_devices.at[selected_device_index, 'POS']))
        location_options = filtered_devices['LOCATION'].unique()
        location = col1.selectbox("Location", location_options, index=location_options.tolist().index(filtered_devices.at[selected_device_index, 'LOCATION']))
        friendly_name = col1.text_input("Friendly Name (ONLY MAIN DEVICES SHOULD HAVE FRIENDLY NAMES)", filtered_devices.at[selected_device_index, 'FRIENDLY NAME'])
        connected_options = filtered_devices['CONNECTED'].unique()
        connected = col1.selectbox("Main Device Name", connected_options, index=connected_options.tolist().index(filtered_devices.at[selected_device_index, 'CONNECTED']))
        notes = col1.text_input("Notes", filtered_devices.at[selected_device_index, 'NOTES'])

        # Display existing image if available
        if 'IMAGE' in filtered_devices.columns:
            existing_image = filtered_devices.at[selected_device_index, 'IMAGE']
            if existing_image:
                col2.image(existing_image, use_column_width=True)
                
        # File upload for image in the right column
        image_upload = None
        image_upload = col2.file_uploader("Upload a new photo?", type=["jpg", "jpeg", "png"])

        # Check if an image is uploaded
        if image_upload:
            uploaded_image = Image.open(io.BytesIO(image_upload.read()))
            target_size = (400, 400)
            resized_image = uploaded_image.resize(target_size)
            rotated_image = resized_image.rotate(270, expand=True)
            st.image(rotated_image, caption="Uploaded Image", use_column_width=True)

        if st.button("Save Changes"):
            # Connect to the database
            conn = sqlite3.connect(os.path.join(absolute_path,'POSHardware.db'))
            cursor = conn.cursor()

            try:
                # Fetch the current values before the update
                fetch_old_values_query = "SELECT POS, LOCATION, `FRIENDLY NAME`, CONNECTED, NOTES, IMAGE FROM CURRENT WHERE `S/N` = ?;"
                old_values = cursor.execute(fetch_old_values_query, (selected_device_serial,)).fetchone()
                
                # Convert the image to bytes if it's uploaded
                image_bytes = image_upload.read() if image_upload else old_values[5]

                # Update the data in the SQL database
                update_query = f"UPDATE CURRENT SET POS = ?, LOCATION = ?, `FRIENDLY NAME` = ?, CONNECTED = ?, NOTES = ?, IMAGE = ?, `LAST EDIT` = ? WHERE `S/N` = ?;"
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(update_query, (pos, location, friendly_name, connected, notes, image_bytes, timestamp, selected_device_serial))

                # Insert the old values into the HISTORY table
                insert_history_query = "INSERT INTO HISTORY ('CHANGE TIME', 'DEVICE S/N', 'PREVIOUS LOCATION', 'PREVIOUS FRIENDLY NAME', 'PREVIOUS CONNECTION', 'PREVIOUS NOTES', 'PREVIOUS PHOTO', 'NEW LOCATION', 'NEW FRIENDLY NAME', 'NEW CONNECTION', 'NEW NOTES', 'NEW PHOTO') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
                cursor.execute(insert_history_query, (timestamp, selected_device_serial, old_values[1], old_values[2], old_values[3], old_values[4], old_values[5], location, friendly_name, connected, notes, image_bytes))

                # Commit the changes
                conn.commit()
                st.success("Changes saved successfully!")

                # Refresh the data in the app
                df_current = load_data("CURRENT")
                df_history = load_data("HISTORY")

            except sqlite3.Error as e:
                st.error(f"Error updating data: {e}")

            finally:
                # Close the connection
                conn.close()

with history:
    st.subheader('History Data')

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

    # Filter history data based on search input across all columns
    if search_history:
        filtered_history = df_history[df_history.apply(lambda row: any(row.astype(str).str.contains(search_history, case=False)), axis=1)]
        st.dataframe(filtered_history, use_container_width=True, hide_index=True)
    else:
        # Display all history data
        st.dataframe(df_history, use_container_width=True, hide_index=True, column_order=("CHANGE TIME","DEVICE S/N","PREVIOUS LOCATION","PREVIOUS FRIENDLY NAME", "PREVIOUS CONNECTION","PREVIOUS NOTES","NEW LOCATION","NEW FRIENDLY NAME","NEW CONNECTION","NEW NOTES"))

    # Close the connection
    conn.close()
