from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, send_file
import pymysql
from werkzeug.utils import secure_filename
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, redirect, url_for
import datetime
from flask_mail import Mail, Message
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from flask_paginate import Pagination, get_page_args
import hashlib

app = Flask(__name__)
app.secret_key = 'b1fd2e52903ba3d848b4ca718c9e2d2f08a94fa7d8721aa1'

db_host = '35.193.112.222'  # Use your Google Cloud SQL instance's IP address
db_user = 'root'
db_password = 'root'  # Replace with your actual password
db_name = 'astra'

# Your database configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'

def get_db_connection():
    connection = pymysql.connect(host=db_host, user=db_user, password=db_password, db=db_name, cursorclass=pymysql.cursors.DictCursor)
    return connection


@app.route('/admin/admin_add_slots', methods=['GET'])
def admin_input_slots():
    # Fetch property listings from the 'properties' table, including the location
    db_connection = get_db_connection()  # Assuming this function returns a database connection
    cursor = db_connection.cursor()
    cursor.execute("SELECT ListingID, name, location FROM properties")
    properties = cursor.fetchall()
    cursor.close()
    db_connection.close()
    return render_template('/admin/admin_input_slots.html', properties=properties)

@app.route('/admin/submit_slots', methods=['POST'])
def admin_submit_slots():
    if request.method == 'POST':
        property_id = request.form['property']
        slot_type = request.form['slot_type']
        availability_status = request.form['availability_status']
        parcel = request.form['parcel']
        block = request.form['block']
        slot = request.form['slot']

        # Get a database connection
        db_connection = get_db_connection()

        try:
            # Create a cursor
            cursor = db_connection.cursor()

            # Check if the slot already exists for the given property
            cursor.execute(
                "SELECT SlotID FROM properties_slots WHERE ListingID = %s AND Parcel = %s AND Block = %s AND Slot = %s",
                (property_id, parcel, block, slot)
            )
            existing_slot = cursor.fetchone()

            if existing_slot:
                # If the slot already exists, flash an error message and show the error toast
                property_name = get_property_name(property_id)  # Replace with a function to get the property name
                property_location = get_property_location(property_id)  # Add function to get property location
                flash(f"The slot {slot} already exists for the property {property_name} - {property_location}. Please enter a different slot.", 'danger')
                return redirect(url_for('admin_input_slots', error=True))
            else:
                # Insert the data into the 'properties_slots' table
                cursor.execute(
                    "INSERT INTO properties_slots (ListingID, slot_type, availability_status, Parcel, Block, Slot) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (property_id, slot_type, availability_status, parcel, block, slot)
                )

                # Commit the transaction
                db_connection.commit()

                # Close the cursor and connection
                cursor.close()
                db_connection.close()

                # Flash a success message and show the success toast
                flash(f"Slot {slot} added successfully!", 'success')
                return redirect(url_for('admin_input_slots', success=True))
        except Exception as e:
            # If an error occurs, flash an error message and show the error toast
            flash('Failed to add the slot. Please try again.', 'danger')
            return redirect(url_for('admin_input_slots', error=True))

def get_property_name(property_id):
    db_connection = get_db_connection()

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM properties WHERE ListingID = %s", (property_id,))
        property = cursor.fetchone()
        if property:
            return property[0]  # Return the name
    except Exception as e:
        print("Error getting property name:", str(e))
    finally:
        cursor.close()
        db_connection.close()
    return None  # Return None if the property is not found

def get_property_location(property_id):
    db_connection = get_db_connection()

    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT location FROM properties WHERE ListingID = %s", (property_id,))
        property_location = cursor.fetchone()
        if property_location:
            return property_location[0]  # Return the location
    except Exception as e:
        print("Error getting property location:", str(e))
    finally:
        cursor.close()
        db_connection.close()
    return None  # Return None if the property is not found





@app.route('/admin/admin_properties_slots', methods=['GET'])
def admin_properties_slots():
    # Fetch slots from the 'properties_slots' table
    db_connection = get_db_connection()  # Assuming this function returns a database connection
    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT ps.SlotID, ps.ListingID, p.name AS property_name, p.location AS property_location, "
        "ps.slot_type, ps.availability_status, ps.Parcel, ps.Block, ps.Slot "
        "FROM properties_slots ps "
        "INNER JOIN properties p ON ps.ListingID = p.ListingID"
    )
    slots = cursor.fetchall()
    cursor.close()
    db_connection.close()
    return render_template('/admin/admin_properties_slots.html', slots=slots)

@app.route('/admin/edit_slot/<int:slot_id>', methods=['GET', 'POST'])
def admin_edit_slot(slot_id):
    if request.method == 'GET':
        # Fetch the slot based on slot_id
        db_connection = get_db_connection()
        cursor = db_connection.cursor()
        cursor.execute("SELECT * FROM properties_slots WHERE SlotID = %s", (slot_id,))
        slot = cursor.fetchone()
        cursor.close()
        db_connection.close()

        return render_template('/admin/admin_edit_properties_slots.html', slot=slot)
    
    if request.method == 'POST':
        # Handle slot editing form submission here
        slot_type = request.form['slot_type']
        availability_status = request.form['availability_status']
        parcel = request.form['parcel']
        block = request.form['block']
        slot = request.form['slot']

        # Update the slot details in the 'properties_slots' table
        db_connection = get_db_connection()
        cursor = db_connection.cursor()
        cursor.execute(
            "UPDATE properties_slots SET  slot_type = %s, availability_status = %s, Parcel = %s, Block = %s, Slot = %s "
            "WHERE SlotID = %s",
            ( slot_type, availability_status, parcel, block, slot, slot_id)
        )
        db_connection.commit()
        cursor.close()
        db_connection.close()

        # Redirect to the slot management page or a success page
        flash('Slot updated successfully', 'success')
        return redirect(url_for('admin_properties_slots'))

@app.route('/admin/delete_slot/<int:slot_id>', methods=['GET'])
def admin_delete_slot(slot_id):
    # Delete the slot based on slot_id from the 'properties_slots' table
    db_connection = get_db_connection()
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM properties_slots WHERE SlotID = %s", (slot_id,))
    db_connection.commit()
    cursor.close()
    db_connection.close()
    return redirect(url_for('admin_properties_slots'))


@app.route('/index')
def index():
    # Establish a database connection
    connection = get_db_connection()

    # Prepare a cursor to execute SQL queries
    cursor = connection.cursor()

    # Query to select the first three properties from the database
    query = "SELECT * FROM properties LIMIT 3"

    # Execute the query
    cursor.execute(query)

    # Fetch the first three properties as a list of dictionaries
    featured_properties = cursor.fetchall()

    # Close the cursor and database connection
    cursor.close()
    connection.close()

    # Render an HTML template and pass the featured property data to it
    return render_template('index.html', featured_properties=featured_properties)



@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/v_tour')
def v_tour():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
    SELECT p.*, 
           CASE WHEN vi.image_data IS NOT NULL THEN 1 ELSE 0 END AS has_virtual_tour
    FROM properties AS p
    LEFT JOIN property_virtual_images AS vi ON p.ListingID = vi.PropertyID
""")

            properties = cursor.fetchall()
    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        properties = []
    finally:
        connection.close()
    return render_template('v_tour.html', properties=properties)

@app.route('/virtual_tour/<int:property_id>')
def virtual_tour(property_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Retrieve virtual tour images associated with the property
            cursor.execute("SELECT image_data FROM property_virtual_images WHERE PropertyID = %s", (property_id,))
            virtual_tour_images = cursor.fetchall()
    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        virtual_tour_images = []
    finally:
        connection.close()

    if virtual_tour_images:
        # Pass the virtual_tour_images data to the template
        return render_template('virtual_tour.html', virtual_tour_images=virtual_tour_images)
    else:
        return "Virtual tour not found or an error occurred"

@app.route('/agent/agent_logout', methods=['GET'])
def agent_logout():
    # Clear the agent's session data
    session.clear()
    
    # Redirect to the agent login page or any other page after logout
    return redirect('/agent/agent_login')  # Replace '/agent_login' with your agent login page URL


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))  # Redirect to the admin login page

@app.route('/loancal', methods=['GET', 'POST'])
def loancal():
    if request.method == 'POST':
    # Handle the form submission and calculate the loan details here
    # You'll need to extract form data (loan amount, down payment, interest rate, loan term) and perform calculations
    # Calculate monthly payments, total payment, etc.
    
    # Sample calculation (replace this with your actual calculation logic)
        loan_amount = float(request.form.get('loan_amount'))
        down_payment = float(request.form.get('down_payment'))
        interest_rate = float(request.form.get('interest_rate'))  # Parse as a float
        loan_term = int(request.form.get('loan_term'))

    # Calculate monthly payment with loan term in years
    loan_term_years = int(request.form.get('loan_term'))
    loan_term_months = loan_term_years * 12  # Convert years to months
    monthly_payment_without_down_payment = calculate_monthly_payment(loan_amount - down_payment, interest_rate / 100, loan_term_months)

    # Calculate total payment with loan term in years
    total_payment_without_down_payment = monthly_payment_without_down_payment * loan_term_months

    # Calculate loan amount without down payment
    loan_without_down_payment = loan_amount  # No need to subtract down payment here

    # Pass the calculated values to the template and return it
    return render_template('loancal.html',
                           loan_amount=loan_amount + down_payment,  # Add down payment back for display
                           down_payment=down_payment,
                           interest_rate=interest_rate,  # Keep it as a float
                           loan_term=loan_term,
                           monthly_payment=monthly_payment_without_down_payment,
                           total_payment=total_payment_without_down_payment,
                           loan_without_down_payment=loan_without_down_payment)



# The calculate_monthly_payment function remains the same as before
def calculate_monthly_payment(loan_amount, interest_rate, loan_term):
    monthly_interest_rate = interest_rate / 12
    monthly_payment = (loan_amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -loan_term)
    return monthly_payment

    
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/property_prices')
def property_prices():
    return render_template('property_prices.html')

@app.route('/forgot_password')
def forgot_password():
   return render_template('forgot_password.html')

@app.route('/house_list')
def house_list():
    # Fetch the list of houses from your database or data source
    houses = get_all_houses()  # Implement this function to fetch houses

     # Get the current page from the request's query parameters (default to 1 if not provided)
    page = int(request.args.get('page', 1))

    # Number of items to display per page
    per_page = 10

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Fetch the list of houses from your database or data source
    houses = get_all_houses()[start_idx:end_idx]  # Implement this function to fetch houses

    # Calculate the total number of pages
    total_houses = len(get_all_houses())  # Implement this function to get the total number of houses
    total_pages = (total_houses + per_page - 1) // per_page
    return render_template('house_list.html', houses=houses, current_page=page, total_pages=total_pages)

def get_all_houses():
    try:
        # Establish a database connection
        connection = get_db_connection()  # Implement this function to create a database connection

        # Create a cursor to execute SQL queries
        with connection.cursor() as cursor:
            # Define the SQL query to fetch all houses
            sql = "SELECT * FROM properties"

            # Execute the SQL query
            cursor.execute(sql)

            # Fetch all rows (houses) from the result set
            houses = cursor.fetchall()

        return houses
    except pymysql.Error as e:
        # Handle any database errors (e.g., log the error, display an error message)
        print(f"Database Error: {str(e)}")
        return []
    finally:
        # Close the database connection when done
        if connection:
            connection.close()

@app.route('/static/<filename>')
def uploaded_file(filename):
    return send_from_directory('/', filename)

# Define a function to check if the user is an admin
def user_is_admin():
    return session.get('UserType') == 'admin'

@app.route('/admin/admin_schedule_input', methods=['GET', 'POST'])
def admin_schedule_input():
    # Check if the user is an admin
    if not user_is_admin():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        AgentID = request.form['AgentID']
        DayOfMonth = request.form['DayOfMonth']  # Change DayOfWeek to DayOfMonth
        Month = request.form['Month']
        Year = request.form['Year']
        StartTime = request.form['StartTime']
        EndTime = request.form['EndTime']

        # Create a database connection
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Check if the schedule already exists for the given day, agent, and time
                check_query = "SELECT * FROM agents_schedule WHERE AgentID = %s AND DayOfMonth = %s AND Month = %s AND Year = %s AND StartTime = %s"
                cursor.execute(check_query, (AgentID, DayOfMonth, Month, Year, StartTime))
                existing_schedule = cursor.fetchone()

                if existing_schedule:
                    flash('Schedule already exists for this agent, day, and time.', 'danger')
                else:
                    # Insert a new schedule entry
                    insert_query = "INSERT INTO agents_schedule (AgentID, DayOfMonth, Month, Year, StartTime, EndTime) VALUES (%s, %s, %s, %s, %s, %s)"
                    cursor.execute(insert_query, (AgentID, DayOfMonth, Month, Year, StartTime, EndTime))
                    connection.commit()
                    flash('Schedule added successfully!', 'success')
        finally:
            connection.close()

    # Fetch agents to populate the dropdown
    connection = get_db_connection()
    agents = []
    try:
        with connection.cursor() as cursor:
            # Fetch agents from your 'agents' table
            cursor.execute("SELECT AgentID, FirstName, LastName, RealtyAffiliation FROM agents")
            agent_data = cursor.fetchall()
            # Create a list of tuples (AgentID, Full Name, Realty Affiliation) for dropdown options
            agents = [(agent[0], f"{agent[1]} {agent[2]} ({agent[3]})", agent[3]) for agent in agent_data]
    finally:
        connection.close()
    return render_template('/admin/admin_schedule_input.html', agents=agents)



@app.route('/admin/edit_schedule/<int:agent_id>', methods=['GET', 'POST'])
def edit_schedule(agent_id):
    # Check if the user is an admin
    if not user_is_admin():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Fetch the agent's schedule from the database using agent_id
    agent_schedule = get_agent_schedule_by_id(agent_id)
    
    # Fetch agent details (agent_name and realty_affiliation)
    agent_name, realty_affiliation = get_agent_details(agent_id)

    if request.method == 'POST':
        # Handle form submission and update the agent's schedule in the database
        updated_schedule_data = {
        'DayOfMonth': request.form['DayOfMonth'],
        'Month': request.form['Month'],
        'Year': request.form['Year'],
        'StartTime': request.form['StartTime'],
        'EndTime': request.form['EndTime'],
        }

        # Update the schedule data in the database
        update_agent_schedule(agent_id, updated_schedule_data)

        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('agents_schedules'))

    return render_template('/admin/edit_schedule.html', agent_schedule=agent_schedule, agent_name=agent_name, realty_affiliation=realty_affiliation)


def get_agent_schedule_by_id(agent_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch the agent's schedule data by AgentID
            cursor.execute("SELECT * FROM agents_schedule WHERE AgentID = %s", (agent_id,))
            agent_schedule = cursor.fetchone()
            return agent_schedule
    finally:
        connection.close()


@app.route('/admin/delete-schedule/<int:agent_id>', methods=['DELETE'])
def delete_schedule(agent_id):
    # Check if the user is an admin
    if not user_is_admin():
        return jsonify({'success': False, 'message': 'You do not have permission to delete schedules.'})

    # Handle the deletion action and delete the agent's schedule from the database
    if request.method == 'DELETE':
        if delete_agent_schedule(agent_id):  # Replace with your delete query
            return jsonify({'success': True, 'message': 'Schedule deleted successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete schedule.'})
    return jsonify({'success': False, 'message': 'Invalid request.'})


@app.route('/admin/agents_schedules')
def agents_schedules():

    agent_schedules = get_agent_schedules()

    # Pass the fetched data to the HTML template
    return render_template('/admin/agents_schedules.html', agent_schedules=agent_schedules)

def get_agent_details(agent_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT FirstName, LastName, RealtyAffiliation FROM agents WHERE AgentID = %s", (agent_id,))
            agent_data = cursor.fetchone()
            if agent_data:
                agent_name = f"{agent_data[0]} {agent_data[1]}"  # Use index to access elements
                realty_affiliation = agent_data[2]  # Use index to access elements
                return agent_name, realty_affiliation
    finally:
        connection.close()


def get_agent_schedules():
    try:
        # Create a database connection
        connection = get_db_connection()

        with connection.cursor() as cursor:
            # Define your SQL query to fetch agent schedules
            query = """
                SELECT
                    agents.AgentID,
                    CONCAT(agents.FirstName, ' ', agents.LastName) AS agent_name,
                    agents.RealtyAffiliation,
                    agents_schedule.DayOfMonth,
                    agents_schedule.Month,
                    agents_schedule.Year,
                    agents_schedule.StartTime,
                    agents_schedule.EndTime
                FROM
                    agents_schedule
                INNER JOIN
                    agents ON agents_schedule.AgentID = agents.AgentID
                ORDER BY
                    agents_schedule.DayOfMonth;
            """

            # Execute the query
            cursor.execute(query)

            # Fetch all agent schedules
            agent_schedules = cursor.fetchall()

            return agent_schedules
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return None
    finally:
        if connection:
            connection.close()
    
def update_agent_schedule(agent_id, updated_data):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Generate the SQL UPDATE query based on the updated_data dictionary
            update_query = "UPDATE agents_schedule SET "
            update_params = []

            for key, value in updated_data.items():
                update_query += f"{key} = %s, "
                update_params.append(value)

            # Remove the trailing comma and space
            update_query = update_query.rstrip(', ')

            # Add the WHERE clause to target the specific agent by AgentID
            update_query += " WHERE AgentID = %s"
            update_params.append(agent_id)

            # Execute the update query
            cursor.execute(update_query, tuple(update_params))
            connection.commit()
    finally:
        connection.close()

def delete_agent_schedule(agent_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Delete the agent's schedule based on AgentID
            cursor.execute("DELETE FROM agents_schedule WHERE AgentID = %s", (agent_id,))
            connection.commit()
    finally:
        connection.close()

def get_available_slots(property_id):
    try:
        # Establish a database connection
        connection = get_db_connection()  # Implement this function to create a database connection

        with connection.cursor() as cursor:
            # Define the SQL query to fetch available slots for the specified property
            sql = """
                SELECT SlotID, slot_type, availability_status, Parcel, Block, Slot
                FROM properties_slots
                WHERE ListingID = %s AND availability_status = 'available'
            """
            cursor.execute(sql, (property_id,))
            available_slots = cursor.fetchall()

            return available_slots


    except pymysql.Error as e:
        # Handle any database errors (e.g., log the error, display an error message)
        print(f"Database Error: {str(e)}")
        return None

    finally:
        # Close the database connection when done
        if connection:
            connection.close()


# Debugging the select_available_agent function
def select_available_agent(visit_date, visit_time):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            query = """
                SELECT AgentID
                FROM agents_schedule
                WHERE StartTime <= %s AND EndTime >= %s
                AND AgentID NOT IN (
                    SELECT AgentID
                    FROM property_visits
                    WHERE VisitDate = %s
                )
                LIMIT 1
            """
            
            # Combine the visit_date and visit_time into a single datetime string
            visit_datetime = f"{visit_date} {visit_time}"

            cursor.execute(query, (visit_datetime, visit_datetime, visit_datetime))
            
            result = cursor.fetchone()

            print("Debug: Available AgentID for", visit_datetime, "is", result)  # Add this line for debugging
            
            if result:
                return result[0]
            else:
                return None
    except Exception as e:
        print("Error:", e)
    finally:
        connection.close()

import json

@app.route('/property/<int:property_id>')
def property_details(property_id):
    property_details = get_property_details(property_id)
    image_filename = property_details[11]
    image_url = url_for('static', filename=f'uploads/{image_filename}')
    property_images = get_property_images(property_id)

    # Check if the user is logged in (you'll need to implement your authentication logic)
    user_is_logged_in = check_user_authentication()  # Replace this with your authentication logic

    # Get available slots for the property
    available_slots = get_available_slots(property_id)
    available_slots_json = json.dumps(available_slots)

    # Create a list of reservation URLs for each available slot
    reservation_urls = [url_for('reservation', property_id=property_id, slot_id=slot[0]) for slot in available_slots]

    return render_template('property_details.html', user_is_logged_in=user_is_logged_in, available_slots_json=available_slots_json, property_details=property_details, image_url=image_url, property_id=property_id, available_slots=available_slots, reservation_urls=reservation_urls, property=property, property_images=property_images)

def check_user_authentication():
    # Check if 'user_id' is present in the session
    user_id = session.get('user_id')

    if user_id is not None:
        # User is logged in
        return True
    else:
        # User is not logged in
        return False
def get_property_images(property_id):
    # Create a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch property images for the specified property_id
    cursor.execute("SELECT image_data FROM property_images WHERE PropertyID = %s", (property_id,))
    images = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return images

def get_property_details(property_id):
    # Create a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch property information for the specified property_id
    cursor.execute("SELECT * FROM properties WHERE ListingID = %s", (property_id,))
    property_details = cursor.fetchone()

    cursor.close()
    conn.close()

    return property_details

@app.route('/reservation/<int:property_id>/<int:slot_id>', methods=['GET', 'POST'])
def reservation(property_id, slot_id):
    print("Slot ID:", slot_id)

    property_details = None
    available_slots = None
    slot_details = None
    reservation_url = url_for('reservation', property_id=property_id, slot_id=slot_id)

    if request.method == 'POST':
        client_name = request.form['client_name']
        client_email = request.form['client_email']
        client_number = request.form['client_number']
        visit_date = request.form['visit_date']
        visit_time = request.form['visit_time']
        parcel = request.form['parcel']
        block = request.form['block']
        slot = request.form['slot']

        # Check if the chosen slot is available
        if is_slot_available(property_id, parcel, block, slot):
            # Validate if the chosen visit time is already reserved
            if is_time_slot_reserved(property_id, f"{visit_date} {visit_time}"):
                flash('The chosen visit time is already reserved. Please choose another time.', 'danger')
            else:
                # Find an available agent based on their schedule
                agent_id = select_available_agent(visit_date, visit_time)

                if agent_id:
                    # Reserve the property slot
                    reserve_successful = reserve_property_slot(property_id, parcel, block, slot)

                    if reserve_successful:
                        print(f"Slot ID: {slot_id}")
                        # Insert the visit reservation into the 'property_visits' table with the assigned agent
                        reservation_successful = reserve_property_visit(
                            property_id,
                            client_name,
                            client_email,
                            client_number,
                            visit_date,  # Use visit_date directly
                            visit_time,  # Use visit_time directly
                            agent_id,
                            slot_id  # Pass slot_id to the function
                        )

                        if reservation_successful:
                            flash('Visit and property slot reserved successfully!', 'success')
                        else:
                            flash('Failed to reserve visit. Please try again.', 'danger')
                    else:
                        flash('Failed to reserve property slot. Please try again.', 'danger')
                else:
                    flash('No available agents for the selected time. Please choose another time.', 'danger')
        else:
            flash('The chosen property slot is already reserved. Please choose another slot.', 'danger')

        property_details = get_property_details(property_id)
        available_slots = get_available_slots(property_id)

        # Retrieve the selected slot details based on the slot_id in the request
        if slot_id:
            slot_details = get_slot_details(slot_id)

    # If it's a GET request, fetch the property and slot details
    if not property_details:
        property_details = get_property_details(property_id)
    if not available_slots:
        available_slots = get_available_slots(property_id)
    
    # Fetch slot details using the slot_id
    if not slot_details and slot_id:
        slot_details = get_slot_details(slot_id)

    return render_template('reservation.html', property_id=property_id, property_details=property_details, available_slots=available_slots, reservation_url=reservation_url, slot_details=slot_details, slot_id=slot_id)


# The rest of your code remains the same

def get_slot_details(slot_id):
    try:
        connection = get_db_connection()  # Define your database connection function

        with connection.cursor() as cursor:
            # Query the database to get slot details based on slot_id
            sql = """
                SELECT Parcel, Block, Slot
                FROM properties_slots
                WHERE SlotID = %s
            """
            cursor.execute(sql, (slot_id,))
            result = cursor.fetchone()

            if result:
                parcel, block, slot = result
                return parcel, block, slot
            else:
                return None
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return None
    finally:
        if connection:
            connection.close()

def get_property_slots(property_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT SlotID, slot_type, availability_status, Parcel, Block, Slot
                FROM properties_slots
                WHERE ListingID = %s AND availability_status = 'available'
            """
            cursor.execute(sql, (property_id,))
            return cursor.fetchall()
    finally:
        connection.close()

# Function to check if a property slot is available
def is_slot_available(property_id, parcel, block, slot):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query the 'properties_slots' table to check if the slot is available
            sql = """
                SELECT availability_status
                FROM properties_slots
                WHERE ListingID = %s AND Parcel = %s AND Block = %s AND Slot = %s
            """
            cursor.execute(sql, (property_id, parcel, block, slot))
            result = cursor.fetchone()
            
            if result:
                return result[0] == 'available'
            else:
                return False  # If the slot doesn't exist, it's not available
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return False  # Assume the slot is not available in case of an error
    finally:
        if connection:
            connection.close()

def is_time_slot_reserved(property_id, visit_datetime):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query the 'property_visits' table to check for existing reservations
            sql = """
                SELECT COUNT(*) FROM property_visits
                WHERE PropertyID = %s AND VisitDate = %s AND Status = 'Scheduled'
            """
            cursor.execute(sql, (property_id, visit_datetime))
            result = cursor.fetchone()
            return result[0] > 0  # If result[0] > 0, the time slot is reserved
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return True  # Assume the time slot is reserved in case of an error
    finally:
        if connection:
            connection.close()


def reserve_property_slot(ListingID, parcel, block, slot):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Update the availability status to 'reserved'
            sql = """
                UPDATE properties_slots
                SET availability_status = 'reserved'
                WHERE ListingID = %s AND Parcel = %s AND Block = %s AND Slot = %s
            """
            cursor.execute(sql, (ListingID, parcel, block, slot))
            connection.commit()
            return True
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return False

    finally:
        if connection:
            connection.close()

# Function to insert a visit reservation into the database
def reserve_property_visit(property_id, client_name, client_email, client_number, visit_date, visit_time, agent_id, slot_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Insert the visit reservation into the 'property_visits' table
            sql = """
                INSERT INTO property_visits (PropertyID, ClientName, ClientEmail, ClientNumber, VisitDate, VisitTime, Status, AgentID, SlotID)
                VALUES (%s, %s, %s, %s, %s, %s, 'Scheduled', %s, %s)
            """
            cursor.execute(sql, (property_id, client_name, client_email, client_number, visit_date, visit_time, agent_id, slot_id))
            connection.commit()
            return True  # Reservation successful
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return False  # Reservation failed
    finally:
        if connection:
            connection.close()

def get_property_details(property_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Retrieve property details based on the given property_id
            sql = "SELECT * FROM properties WHERE ListingID = %s"
            cursor.execute(sql, (property_id,))
            property_details = cursor.fetchone()
            return property_details  # Returns a dictionary of property details
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return None  # Return None in case of an error
    finally:
        if connection:
            connection.close()
        
def get_featured_properties():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Execute a SQL query to fetch featured properties
            sql = "SELECT * FROM properties WHERE is_featured = 1"  # Assuming 1 means featured in the database
            cursor.execute(sql)
            featured_properties = cursor.fetchall()
        return featured_properties
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
        return []
    finally:
        connection.close()

def get_user_generated_content():
    try:
        connection = get_db_connection()  # Create a connection (you should already have this function)
        with connection.cursor() as cursor:
            # Execute a query to fetch user-generated content (adjust the query to your schema)
            sql = "SELECT id, content_type FROM user_generated_content"
            cursor.execute(sql)
            user_generated_content = cursor.fetchall()
        return user_generated_content
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
        return []
    finally:
        connection.close()  # Close the database connection when done

# Function to get users from the database (you need to implement this)
def get_users_from_database():
    try:
        connection = get_db_connection()  # Create a connection (you should already have this function)
        with connection.cursor() as cursor:
            # Execute a query to fetch users (adjust the query to your schema)
            sql = "SELECT * FROM users"
            cursor.execute(sql)
            users = cursor.fetchall()
        return users
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
        return []
    finally:
        connection.close()  # Close the database connection when done

@app.route('/admin/admin_dashboard')
def admin_dashboard():
    admin_username = get_admin_username()
    total_users = get_total_users_count()
    active_users = get_active_users_count()
    new_users_past_month = get_new_users_past_month_count()

    return render_template('admin/admin_dashboard.html', admin_username=admin_username, total_users=total_users, active_users=active_users, new_users_past_month=new_users_past_month)

def get_total_users_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
        return total_users
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return 0
    finally:
        if connection:
            connection.close()

def get_active_users_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active_users = cursor.fetchone()[0]
        return active_users
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return 0
    finally:
        if connection:
            connection.close()

def get_new_users_past_month_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Calculate the date one month ago from the current date
            one_month_ago = datetime.today() - timedelta(days=30)

            # Query for new users in the past month
            cursor.execute("SELECT COUNT(*) FROM users WHERE registration_date >= %s", (one_month_ago,))
            new_users_past_month = cursor.fetchone()[0]
        return new_users_past_month
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return 0
    finally:
        if connection:
            connection.close()

@app.route('/admin/admin_user_management')
def admin_user_management():
    user_generated_content = get_user_generated_content()
    admin_username = get_admin_username()

    # Get the role parameter from the URL
    role = request.args.get('role')
    
    # Retrieve users based on the specified role
    if role:
        users = get_users_by_role(role)
    else:
        users = get_users_from_database()  # Retrieve all users if no role is specified

    # Get the search query from the request
    search_query = request.args.get('search_query', '')

    # Filter users based on the search query (you can customize this filter logic)
    users = filter_users(users, search_query)

    # Pagination logic
    page = request.args.get('page', 1, type=int)  # Get the current page from the request
    per_page = 10  # Number of items to display per page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    total_users = len(users)  # Total number of users after filtering
    total_pages = (total_users + per_page - 1) // per_page

    # Slice the users to show only the items for the current page
    users = users[start_idx:end_idx]

    return render_template('admin/admin_user_management.html', users=users, user_generated_content=user_generated_content, admin_username=admin_username, current_page=page, total_pages=total_pages)

def filter_users(users, search_query):
    filtered_users = []
    
    for user in users:
        # Customize this logic to match your filtering criteria
        if search_query.lower() in user[2].lower():
            filtered_users.append(user)
    
    return filtered_users

def get_users_by_role(role):
    try:
        connection = get_db_connection()  # Create a database connection

        with connection.cursor() as cursor:
            # Execute a SQL query to fetch users by role
            sql = "SELECT * FROM users WHERE UserType = %s"
            cursor.execute(sql, (role,))
            users = cursor.fetchall()

        return users
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return []
    finally:
        if connection:
            connection.close()  # Close the database connection when done

@app.route('/admin/admin_reservation')
def admin_reservation():
    # Fetch all property visits from your data source
    all_property_visits = get_property_visits()  # Implement this function to fetch all property visits

    # Get the current page from the request's query parameters (default to 1 if not provided)
    page = int(request.args.get('page', 1))

    # Number of items to display per page
    per_page = 10

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Filter property visits based on the search query (you can customize this filter logic)
    search_query = request.args.get('search_query', '')
    property_visits = filter_property_visits(all_property_visits, search_query)

    # Slice the property visits to show only the items for the current page
    property_visits = property_visits[start_idx:end_idx]

    # Calculate the total number of pages based on the total number of property visits (not filtered)
    total_visits = len(all_property_visits)  # Using the unfiltered list for counting
    total_pages = (total_visits + per_page - 1) // per_page

    
    return render_template('admin/admin_reservation.html', property_visits=property_visits, current_page=page, total_pages=total_pages)


def filter_property_visits(property_visits, search_query):
    # Create an empty list to store filtered property visits
    filtered_visits = []

    # Iterate through each property visit
    for visit in property_visits:
        # Check if the client name in lowercase contains the search query in lowercase
        if search_query.lower() in visit[2].lower():  # Assuming visit[2] contains the client name
            # If the client name matches the search query, add it to the filtered list
            filtered_visits.append(visit)

    return filtered_visits

def get_property_visits():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM property_visits"
            cursor.execute(sql)
            property_visits = cursor.fetchall()
        return property_visits
    except pymysql.Error as e:
        print(f"Error: {str(e)}")
        return []
    finally:
        connection.close()

@app.route('/admin/edit_visit_status/<int:VisitID>', methods=['POST'])
def edit_visit_status(VisitID):
    if request.method == 'POST':
        new_status = request.form['status']
        original_status = request.form['original_status']

        # Check if the status has changed
        if new_status != original_status:
            # Update the status in the database (you'll need to implement this)
            update_visit_status(VisitID, new_status)  # Replace with your logic to update the status

            # Flash a success message
            flash('Visit status updated successfully', 'success')
        else:
            # Flash a message indicating that the status didn't change
            flash('Visit status remains the same', 'info')
        
    return redirect('/admin/admin_reservation')

def update_visit_status(VisitID, new_status):
    try:
        connection = get_db_connection()  # Create a database connection
        with connection.cursor() as cursor:
            # Execute a SQL update query to change the visit status
            sql = "UPDATE property_visits SET Status = %s WHERE VisitID = %s"
            cursor.execute(sql, (new_status, VisitID))
            connection.commit()  # Commit the changes to the database
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
    finally:
        connection.close()  # Close the database connection when done

def get_admin_username():
    try:
        connection = get_db_connection()  # Create a database connection
        with connection.cursor() as cursor:
            # Execute a SQL query to fetch the admin's username
            sql = "SELECT Username FROM users WHERE UserType = 'admin' LIMIT 1"
            cursor.execute(sql)
            admin_username = cursor.fetchone()  # Fetch the admin's username
            return admin_username[0] if admin_username else None
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
        return None
    finally:
        connection.close()  # Close the database connection when done
  

# Function to update the user's role in the database
def update_user_role(user_id, new_role):
    try:
        connection = get_db_connection()  # Create a database connection
        with connection.cursor() as cursor:
            # Execute a SQL update query to change the user's role
            sql = "UPDATE users SET UserType = %s WHERE UserID = %s"
            cursor.execute(sql, (new_role, user_id))
            connection.commit()  # Commit the changes to the database

            # Flash a success message
            flash('User role updated successfully!', 'success')
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
        # Flash an error message
        flash('An error occurred while updating the user role.', 'danger')
    finally:
        connection.close()  # Close the database connection when done

# Function to fetch a user by ID from the database
def get_user_by_id(user_id):
    try:
        connection = get_db_connection()  # Create a database connection
        with connection.cursor() as cursor:
            # Execute a SQL query to fetch a user by ID
            sql = "SELECT id, username, email, role FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()  # Fetch one user
            return user
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
        return None
    finally:
        connection.close()  # Close the database connection when done

# Function to deactivate a user by ID in the database
def deactivate_user_by_id(user_id):
    try:
        connection = get_db_connection()  # Create a database connection
        with connection.cursor() as cursor:
            # Execute a SQL update query to deactivate the user
            sql = "UPDATE users SET is_active = 0 WHERE id = %s"
            cursor.execute(sql, (user_id,))
            connection.commit()  # Commit the changes to the database
    except pymysql.Error as e:
        # Handle the error (e.g., log it or display an error message)
        print(f"Error: {str(e)}")
    finally:
        connection.close()

@app.route('/admin/add_property', methods=['GET', 'POST'])
def add_property():
    if request.method == 'POST':
        # Extract property data from the form
        name = request.form['name']
        property_type = request.form['type']
        province = request.form['province']
        price = Decimal(request.form['price'])
        beds = int(request.form['beds'])
        toilet_bath = int(request.form['toilet_bath'])
        description = request.form['description']
        lot_area = Decimal(request.form['lot_area'])
        floor_area = Decimal(request.form['floor_area'])
        location = request.form['location']

        # Handle file uploads for property images
        property_image_data = []
        virtual_tour_image_data = []

        if 'image' in request.files:
            property_images = request.files.getlist('image')
            for image in property_images:
                if image.filename != '':
                    # Securely save the uploaded image
                    image_filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    property_image_data.append(image_filename)

        if 'virtual_tour_images' in request.files:
            virtual_tour_images = request.files.getlist('virtual_tour_images')
            for virtual_tour_image in virtual_tour_images:
                if virtual_tour_image.filename != '':
                    # Securely save the uploaded virtual tour image
                    virtual_tour_image_filename = secure_filename(virtual_tour_image.filename)
                    virtual_tour_image.save(os.path.join(app.config['UPLOAD_FOLDER'], virtual_tour_image_filename))
                    virtual_tour_image_data.append(virtual_tour_image_filename)

        if 'thumbnail' in request.files:
            thumbnail = request.files['thumbnail']
            if thumbnail.filename != '':
                # Securely save the uploaded thumbnail image
                thumbnail_filename = secure_filename(thumbnail.filename)
                thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename))

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Insert property data into the properties table
                sql = """
                    INSERT INTO properties (name, type, province, price, beds, toilet_bath, lot_area, floor_area, description, location, thumbnail_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (name, property_type, province, price, beds, toilet_bath, lot_area, floor_area, description, location, thumbnail_filename))
                connection.commit()

                # Retrieve the ID of the newly added property
                property_id = cursor.lastrowid

                # Insert image paths into the property_images table
                for image_data in property_image_data:
                    cursor.execute(
                        "INSERT INTO property_images (PropertyID, image_data) VALUES (%s, %s)",
                        (property_id, image_data)
                    )

                # Insert virtual tour image paths into the property_virtual_images table
                for virtual_tour_image_data in virtual_tour_image_data:
                    cursor.execute(
                        "INSERT INTO property_virtual_images (PropertyID, image_data) VALUES (%s, %s)",
                        (property_id, virtual_tour_image_data)
                    )

                connection.commit()

                flash('Property added successfully!', 'success')
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            connection.close()

    return render_template('/admin/add_property.html')

@app.route('/admin/properties', methods=['GET'])
def list_properties():
    # Retrieve properties from the database
    properties = get_properties_from_database()

    # Get the current page from the request's query parameters (default to 1 if not provided)
    page = int(request.args.get('page', 1))

    # Number of items to display per page
    per_page = 10

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Slice the properties to show only the items for the current page
    properties = properties[start_idx:end_idx]

    # Calculate the total number of pages based on the total number of properties
    total_properties = len(properties)
    total_pages = (total_properties + per_page - 1) // per_page

    return render_template('/admin/property_list.html', properties=properties, current_page=page, total_pages=total_pages)



def get_property_image(property_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Fetch the image data from the property_images table
        sql = "SELECT image_data FROM property_images WHERE property_id = %s"
        cursor.execute(sql, (property_id,))
        result = cursor.fetchone()
        if result:
            return result[0]  # Return the image data
    return None

@app.route('/admin/edit_property/<int:property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        try:
            # Extract property data from the form
            name = request.form['name']
            property_type = request.form['type']
            province = request.form['province']
            price = Decimal(request.form['price'])
            beds = int(request.form['beds'])
            toilet_bath = int(request.form['toilet_bath'])
            description = request.form['description']
            lot_area = Decimal(request.form['lot_area'])
            floor_area = Decimal(request.form['floor_area'])
            location = request.form['location']

            # Handle thumbnail image upload
            if 'thumbnail' in request.files:
                thumbnail = request.files['thumbnail']
                if thumbnail.filename != '':
                    filename = secure_filename(thumbnail.filename)
                    thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    thumbnail_filename = filename
                else:
                    thumbnail_filename = None

            # Handle property image upload
            if 'image' in request.files:
                image = request.files.getlist('image')
                image_filenames = []  # Create a list to store image file names
                for file in image:
                    if file.filename != '':
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        image_filenames.append(filename)

            # Update property details in the database
            sql = """
                UPDATE properties
                SET name = %s, type = %s, province = %s, price = %s, beds = %s,
                    toilet_bath = %s, description = %s,
                    location = %s, thumbnail_path = %s, lot_area = %s, floor_area = %s
                WHERE ListingID = %s
            """

            cursor.execute(sql, (name, property_type, province, price, beds, toilet_bath,
                                 description, location, thumbnail_filename, lot_area, floor_area, property_id))

            # Update property images
            for image_filename in image_filenames:
                cursor.execute(
                    "INSERT INTO property_images (PropertyID, image_data) VALUES (%s, %s)",
                    (property_id, image_filename)
                )

            # Update virtual tour images
            if 'virtual_tour_images' in request.files:
                virtual_tour_images = request.files.getlist('virtual_tour_images')
                virtual_tour_image_filenames = []  # Create a list to store virtual tour image file names
                for file in virtual_tour_images:
                    if file.filename != '':
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        virtual_tour_image_filenames.append(filename)

                # Insert virtual tour image paths into the property_virtual_images table
                for virtual_tour_image_filename in virtual_tour_image_filenames:
                    cursor.execute(
                        "INSERT INTO property_virtual_images (PropertyID, image_data) VALUES (%s, %s)",
                        (property_id, virtual_tour_image_filename)
                    )

            connection.commit()
            flash('Property updated successfully!', 'success')
            return redirect('/admin/properties')
        except Exception as e:
            connection.rollback()
            flash(f'An error occurred while updating the property: {str(e)}', 'danger')
            print(f"Error: {str(e)}")

    cursor.execute("SELECT * FROM properties WHERE ListingID = %s", (property_id,))
    property = cursor.fetchone()

    # Fetch virtual tour images for the property from the property_virtual_images table
    cursor.execute("SELECT image_data FROM property_virtual_images WHERE PropertyID = %s", (property_id,))
    virtual_tour_images = [row[0] for row in cursor.fetchall()]

    connection.close()

    return render_template('/admin/edit_property.html', property=property, virtual_tour_images=virtual_tour_images)


@app.route('/delete_property/<int:property_id>', methods=['POST', 'DELETE'])
def delete_property(property_id):
    if request.method in ['POST', 'DELETE']:
        # Assuming you have a function to delete a property from the database
        success = delete_property_from_database(property_id)

        if success:
            flash('Property deleted successfully!', 'success')
        else:
            flash('Property not found or could not be deleted.', 'error')

        # Redirect to a relevant page after deletion (e.g., a properties listing page)
        return redirect('/admin/properties')

def delete_property_from_database(property_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "DELETE FROM properties WHERE ListingID = %s"  # Use 'ListingID' as the primary key
            result = cursor.execute(sql, (property_id,))
            connection.commit()

            # Check the result of the delete operation to determine success
            if result > 0:
                return True  # Deletion was successful
            else:
                return False  # Property not found

    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return False  # Could not delete property due to database error

    finally:
        if connection:
            connection.close()


def get_property_by_id(property_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM properties WHERE id = %s"
            cursor.execute(sql, (property_id,))
            property = cursor.fetchone()
            return property
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return None  # Return None if there's an error
    finally:
        if connection:
            connection.close()

def get_properties_from_database():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM properties"
            cursor.execute(sql)
            properties = cursor.fetchall()
            return properties
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return None  # Return None if there's an error
    finally:
        if connection:
            connection.close()


@app.route('/agent/agent_profile')
def agent_profile():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Retrieve all agent data
            cursor.execute("SELECT * FROM users WHERE UserType = 'agent' LIMIT 1")
            agent_data = cursor.fetchone()

    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        agent_data = []
    finally:
        connection.close()

    return render_template('/agent/agent_profile.html', agent_data=agent_data)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if request.method == 'POST':
        # Get the edited data from the form
        edited_name = request.form.get('name')
        edited_number = request.form.get('number')
        edited_address = request.form.get('address')
        edited_email = request.form.get('email')
        edited_dob = request.form.get('dob')
        
        # Retrieve the agent's ID from the session
        agent_id = session.get('agent_id')  # Ensure that you set 'agent_id' in the session earlier

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Update the agent's profile information in the 'agents' table
                cursor.execute("UPDATE agents SET FirstName = %s, PhoneNumber = %s, Address = %s, Email = %s, DateOfBirth = %s WHERE AgentID = %s",
                               (edited_name, edited_number, edited_address, edited_email, edited_dob, agent_id))
                connection.commit()
                flash('Profile updated successfully', 'success')
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            connection.close()

    return redirect('/agent/agent_profile')


from werkzeug.security import generate_password_hash

@app.route('/agent_registration', methods=['GET', 'POST'])
def agent_registration():
    if request.method == 'POST':
        # Get form data from the request
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        realty_affiliation = request.form.get('realty_affiliation')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date_of_birth = request.form.get('date_of_birth')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')

        # Handle profile image upload
        profile_image = request.files.get('profile_image')
        if profile_image:
            # Save the uploaded file to a directory of your choice

            # Validate the form data (you can add more validation logic)
            if not username or not password or not email:
                flash('Username, password, and email are required fields.', 'danger')
            else:
                # Check if the email or username is already taken
                try:
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        # Check if the email is already registered
                        email_check_query = "SELECT * FROM agents WHERE Email = %s"
                        cursor.execute(email_check_query, (email,))
                        existing_email = cursor.fetchone()

                        # Check if the username is already taken
                        username_check_query = "SELECT * FROM agents WHERE Username = %s"
                        cursor.execute(username_check_query, (username,))
                        existing_username = cursor.fetchone()

                        if existing_email:
                            flash('Email is already registered. Please use a different email.', 'danger')
                        elif existing_username:
                            flash('Username is already taken. Please choose a different username.', 'danger')
                        else:
                            # Hash the password before storing it
                            hashed_password = generate_password_hash(password, method='sha256')

                            # Insert agent data into the database
                            insert_query = "INSERT INTO agents (Username, PasswordHash, Email, RealtyAffiliation, FirstName, LastName, DateOfBirth, PhoneNumber, Address) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                            cursor.execute(insert_query, (username, hashed_password, email, realty_affiliation, first_name, last_name, date_of_birth, phone_number, address))
                            connection.commit()
                            flash('Registration successful!', 'success')
                except Exception as e:
                    flash(f'Registration failed. Error: {e}', 'danger')
                finally:
                    connection.close()

                return redirect(url_for('agent_login'))

    return render_template('agent_registration.html')

@app.route('/agent/agent_login', methods=['GET', 'POST'])
def agent_login():
    if request.method == 'POST':
        email_or_username = request.form.get('email_or_username')
        password = request.form.get('password')

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Check if the provided email or username exists in the agents table
                cursor.execute("SELECT * FROM agents WHERE Email = %s OR Username = %s", (email_or_username, email_or_username))
                agent = cursor.fetchone()

                if agent:
                    agent_id = agent[0]
                    stored_password_hash = agent[2]

                    if check_password_hash(stored_password_hash, password):
                        session['agent_id'] = agent_id
                        flash('Login successful!', 'success')
                        return redirect('/agent/agent_dashboard')
                    else:
                        flash('Invalid password', 'danger')
                        print("Invalid password:", password)
                else:
                    flash('Invalid email/username or password. Please try again.', 'danger')
                    print("No agent found for:", email_or_username)
        except pymysql.Error as e:
            flash(f"Database Error: {str(e)}", 'danger')
            print("Database Error:", e)
        finally:
            connection.close()

    return render_template('/agent/agent_login.html')


@app.route('/property_list')
def property_list():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM properties")
            properties = cursor.fetchall()
    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        properties = []
    finally:
        connection.close()

    return render_template("property_list.html", properties=properties)

@app.route('/search', methods=['POST'])
def property_search():
    province = request.form.get('province')
    price = request.form.get('price')
    location = request.form.get('location')
        
    query = "SELECT * FROM properties WHERE 1=1"
    parameters = []

    if province:
        query += " AND province = %s"
        parameters.append(province)
    if price:
        query += " AND price <= %s"  # Modify the condition based on your requirements
        parameters.append(price)
    if location:
        query += " AND location = %s"
        parameters.append(location)

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            properties = cursor.fetchall()
    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        properties = []
    finally:
        connection.close()

    return render_template('search_results.html', properties=properties)



# Specify the allowed file extensions for image uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check if a file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        user_type = request.form['user_type']
        
        # Extract other user attributes here
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        phone_number = request.form['phone_number']

        # Handle file upload
        if 'profile_image' in request.files:
            profile_image = request.files['profile_image']
            if profile_image and allowed_file(profile_image.filename):
                filename = secure_filename(profile_image.filename)
                profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_image_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            else:
                flash('Invalid file format for profile image. Allowed formats: png, jpg, jpeg, gif', 'danger')
                return redirect(request.url)
        else:
            # Handle the case where no profile image is provided
            profile_image_url = None

        # Hash the password using PBKDF2-SHA256
        password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "INSERT INTO users (Username, PasswordHash, Email, UserType, FirstName, LastName, DateOfBirth, PhoneNumber, ProfileImageURL) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (username, password_hash, email, user_type, first_name, last_name, date_of_birth, phone_number, profile_image_url))
                connection.commit()
                flash('Registration successful! You can now log in.', 'success')
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            connection.close()
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        passwordhash = request.form['passwordhash']
        email = request.form['email']
        user_type = 'admin'  # Set the user type to 'admin' for admin registrations

        # Extract other admin-specific user attributes here
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        phone_number = request.form['phone_number']

        # Handle file upload if needed

        # Insert the admin user data into the database
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "INSERT INTO users (Username, passwordhash, Email, UserType, FirstName, LastName, DateOfBirth, PhoneNumber) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(sql, (username, passwordhash, email, user_type, first_name, last_name, date_of_birth, phone_number))
                connection.commit()
                flash('Admin registration successful!', 'success')
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            connection.close()
            return redirect(url_for('admin_login'))

    return render_template('admin/register.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # Check if the user is already logged in
    if 'UserType' in session:
        # If the user is already logged in, redirect to the admin dashboard
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        passwordhash = request.form['passwordhash']

        # Authenticate the user using your authentication function
        user_type = authenticate_user(username, passwordhash)

        if user_type == 'admin':
            # If the user is an admin, set the session variable and redirect
            session['UserType'] = user_type
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash(f'Authentication result: {user_type}', 'danger')  # Add this line
            flash('Invalid credentials or not an admin user. Please try again.', 'danger')
            return redirect(url_for('admin_login'))

    return render_template('/admin/login.html')

def authenticate_user(username, passwordhash):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query the user's record by username
            cursor.execute("SELECT UserID, Password, UserType FROM users WHERE Username = %s", (username,))
            user_data = cursor.fetchone()

            if user_data:
                user_id, stored_password, user_type = user_data
                # Check if the entered password matches the stored password (no hashing)
                if passwordhash == stored_password:
                    session['UserType'] = user_type  # Store user type in session
                    session['UserID'] = user_id  # Optionally, store user ID in session
                    return user_type  # Authentication successful, return the user's type
                else:
                    return None  # Password doesn't match
            else:
                return None  # User not found
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return None
    finally:
        if connection:
            connection.close()





def authenticate_user(username, password):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query the user's record by username
            cursor.execute("SELECT UserID, Password, UserType FROM users WHERE Username = %s", (username,))
            user_data = cursor.fetchone()

            if user_data:
                user_id, stored_password, user_type = user_data
                # Check if the entered password matches the stored password (no hashing)
                if password == stored_password:
                    session['UserType'] = user_type  # Store user type in session
                    session['UserID'] = user_id  # Optionally, store user ID in session
                    return user_type  # Authentication successful, return the user's type
                else:
                    return None  # Password doesn't match
            else:
                return None  # User not found
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return None
    finally:
        if connection:
            connection.close()





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE Username = %s", (username,))
                user = cursor.fetchone()
                if user:
                    user_id = user[0]
                    username = user[1]
                    password_hash = user[2]

                    if check_password_hash(password_hash, password):
                        session['user_id'] = user_id
                        flash('Login successful!', 'success')
                        
                        # Redirect clients to their dashboard or another appropriate page
                        return redirect(url_for('index'))
                    else:
                        flash('Invalid password', 'danger')
                else:
                    flash('Invalid username', 'danger')
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            connection.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Remove the 'user_id' key from the session to log the user out
    session.pop('user_id', None)
    
    # Redirect the user to the home page or another appropriate page
    return redirect(url_for('index'))

# Route for the agent dashboard
@app.route('/agent/agent_dashboard')
def agent_dashboard():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query to get the total number of properties
            cursor.execute("SELECT COUNT(*) FROM properties")
            row = cursor.fetchone()
            total_properties = row[0] if row else 0

            # Query to get the agent's username (assuming there is an 'agents' table)
            cursor.execute("SELECT Username FROM agents LIMIT 1")
            row = cursor.fetchone()
            agent_username = row[0] if row else ""

            # Query to get the recent reservations
            cursor.execute("""
                SELECT ClientName, ClientEmail, VisitTime, Status
                FROM property_visits
                WHERE AgentID = (SELECT AgentID FROM agents WHERE Username = %s)
                ORDER BY VisitTime DESC
                LIMIT 5
            """, (agent_username,))
            recent_reservations = cursor.fetchall()

            # Create a list to store modified reservations
            modified_reservations = []
            now = datetime.now().replace(minute=0, second=0, microsecond=0)  # Set time components to 0
            for reservation in recent_reservations:
                visit_time = datetime.strptime(reservation[2], "%H:%M")
                visit_time = visit_time.replace(year=now.year, month=now.month, day=now.day)  # Set the date components to today
                time_difference = now - visit_time
                if time_difference.days == 0 and time_difference.seconds < 3600:
                    # Less than an hour ago
                    minutes = time_difference.seconds // 60
                    time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    # More than an hour ago
                    hours = time_difference.days * 24 + time_difference.seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"

                # Append the modified data to the list
                modified_reservations.append((reservation[0], reservation[1], time_ago, reservation[3]))

    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        total_properties = 0
        agent_username = ""
        modified_reservations = []
    finally:
        connection.close()

    return render_template(
        '/agent/agent_dashboard.html',
        total_properties=total_properties,
        agent_username=agent_username,
        recent_reservations=modified_reservations  # Pass the modified reservations data to the template
    )


def format_relative_date(date_string):
    date = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    time_difference = now - date

    if time_difference.days > 1:
        return f"{time_difference.days} days ago"
    elif time_difference.days == 1:
        return "yesterday"
    elif time_difference.seconds >= 3600:
        hours = time_difference.seconds // 3600
        return f"{hours} hours ago"
    elif time_difference.seconds >= 60:
        minutes = time_difference.seconds // 60
        return f"{minutes} minutes ago"
    elif time_difference.seconds >= 1:
        return f"{time_difference.seconds} seconds ago"
    else:
        return "just now"
        
@app.route('/agent/agent_reservations', methods=['GET'])
def agent_reservations():
    filter_option = request.args.get('filter', 'all')
    search_query = request.args.get('search', '')

    agent_id = session.get('agent_id')

    # Get page number and page size from the request
    page, per_page, offset = get_page_args()

    if agent_id is not None:
        # Use the filter_option, search_query, page, and per_page in the database query
        filtered_reservations = get_filtered_agent_reservations(agent_id, filter_option, search_query)

        # Create a pagination object for filtered_reservations
        pagination = Pagination(page=page, per_page=per_page, total=len(filtered_reservations), record_name='reservations', css_framework='bootstrap4')

        # Pass the filtered_reservations and pagination to the template
        return render_template('/agent/agent_reservations.html', agent_id=agent_id, reservations=filtered_reservations, pagination=pagination)
    else:
        flash('Please log in to access agent reservations.', 'danger')
        return redirect(url_for('agent_login'))


def get_filtered_agent_reservations(agent_id, filter_option, search_query):
    # Initialize an empty list to store the filtered reservations
    filtered_reservations = []

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Base SQL query with joins to retrieve data from multiple tables
            sql = """
            SELECT pv.VisitID, pv.ClientName, pv.ClientEmail, pv.ClientNumber, pv.VisitDate, pv.VisitTime,
                   pv.Status, pv.PropertyID, ps.Parcel, ps.Block, ps.Slot, p.name AS PropertyName, p.location AS PropertyLocation
            FROM property_visits pv
            JOIN properties_slots ps ON pv.SlotID = ps.SlotID
            JOIN properties p ON pv.PropertyID = p.ListingID
            WHERE pv.AgentID = %s
            """

            if filter_option == 'scheduled':
                sql += " AND pv.Status = 'Scheduled'"
            elif filter_option == 'completed':
                sql += " AND pv.Status = 'Completed'"
            elif filter_option == 'canceled':
                sql += " AND pv.Status = 'Canceled'"

            if search_query:
                sql += " AND pv.ClientName LIKE %s"
                cursor.execute(sql, (agent_id, f"%{search_query}%"))
            else:
                cursor.execute(sql, (agent_id,))

            # Fetch the filtered reservations
            filtered_reservations = cursor.fetchall()
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
    finally:
        if connection:
            connection.close()

    return filtered_reservations


def get_paginated_agent_reservations(agent_id, filter_option, search_query, page, reservations_per_page):
    # Calculate the offset to determine the starting reservation for the current page
    offset = (page - 1) * reservations_per_page
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Construct the SQL query for fetching a specific range of reservations
            sql = """
            SELECT *
            FROM property_visits
            WHERE AgentID = %s
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (agent_id, reservations_per_page, offset))
            paginated_reservations = cursor.fetchall()
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        paginated_reservations = []
    finally:
        if connection:
            connection.close()

    return paginated_reservations

@app.route('/agent/reschedule_reservation/<int:visit_id>', methods=['GET', 'POST'])
def reschedule_reservation(visit_id):
    if request.method == 'POST':
        new_date = request.form['new_date']
        new_time = request.form['new_time']
        # Update the reservation in the database with the new date and time
        update_reservation(visit_id, new_date, new_time)
        flash('Reservation rescheduled successfully.', 'success')
        return redirect(url_for('agent_reservations'))

    # Render the form to select a new date and time
    return render_template('/agent/reschedule_reservation.html', visit_id=visit_id)


def update_reservation(visit_id, new_date, new_time):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Update the reservation with the new date and time
            sql = "UPDATE property_visits SET VisitDate = %s, VisitTime = %s WHERE VisitID = %s"
            cursor.execute(sql, (new_date, new_time, visit_id))
            connection.commit()
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
    finally:
        if connection:
            connection.close()


@app.route('/agent/cancel_reservation/<int:visit_id>', methods=['GET'])
def cancel_reservation(visit_id):
    # Update the reservation status in the database to "Cancelled"
    cancel_reservation(visit_id)
    flash('Reservation cancelled successfully.', 'success')
    return redirect(url_for('agent_reservations'))

def cancel_reservation(visit_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Update the reservation status to "Canceled"
            sql = "UPDATE property_visits SET Status = 'Canceled' WHERE VisitID = %s"
            cursor.execute(sql, (visit_id,))
            connection.commit()
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
    finally:
        if connection:
            connection.close()

@app.route('/agent/send_reminders', methods=['GET'])
def send_reminders():
    upcoming_reservations = get_upcoming_reservations()  # Fetch upcoming reservations
    
    mail = Mail(app)  # Initialize Flask-Mail

    for reservation in upcoming_reservations:
        client_email = reservation['client_email']
        message = Message('Reminder: Upcoming Visit', sender='your_email@example.com', recipients=[client_email])
        message.body = 'This is a reminder for your upcoming visit on ' + reservation['visit_date']
        mail.send(message)

    flash('Reminder emails sent to clients.', 'success')
    return redirect(url_for('agent_reservations'))

def get_upcoming_reservations(agent_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Fetch upcoming reservations for the agent
            sql = "SELECT * FROM property_visits WHERE AgentID = %s AND VisitDate >= CURDATE() ORDER BY VisitDate"
            cursor.execute(sql, (agent_id,))
            reservations = cursor.fetchall()
            return reservations
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return []
    finally:
        if connection:
            connection.close()


@app.route('/agent/generate_report', methods=['GET', 'POST'])
def generate_report():
    agent_id = session.get('agent_id')  # Retrieve the agent_id from the session

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        report_data = get_report_data(agent_id, start_date, end_date)

        # Create a Pandas DataFrame and generate the report
        df = pd.DataFrame(report_data)
        report_filename = 'agent_report.xlsx'
        df.to_excel(report_filename, index=False)
        flash('Report generated successfully.', 'success')

        # Provide a download link for the generated report
        return send_file(report_filename)

    return render_template('/agent/agent_reservations.html')  # Change to the appropriate HTML template


def get_report_data(agent_id, start_date, end_date):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Fetch reservation data within the date range for the agent
            sql = "SELECT * FROM property_visits WHERE AgentID = %s AND VisitDate BETWEEN %s AND %s"
            cursor.execute(sql, (agent_id, start_date, end_date))
            report_data = cursor.fetchall()
            return report_data
    except pymysql.Error as e:
        print(f"Database Error: {str(e)}")
        return []
    finally:
        if connection:
            connection.close()

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if user_id:
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM properties WHERE user_id = %s", (user_id,))
                properties = cursor.fetchall()
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
            properties = []
        finally:
            connection.close()
        return render_template('dashboard.html', properties=properties)
    else:
        flash('You must be logged in to access the dashboard.', 'danger')
        return redirect(url_for('login'))

@app.route('/admin/edit_role/<int:UserID>', methods=['GET', 'POST'])
def edit_role(UserID):
    if request.method == 'POST':
        new_role = request.form['new_role']

        if 'delete' in request.form:
            return redirect(f'/admin/delete_user/{UserID}')
       
        update_user_role(UserID, new_role)  

        return redirect('/admin/admin_user_management')
    else:
        
        user = get_user_by_id(UserID)  
        return render_template('admin/edit_role.html', user=user)

@app.route('/admin/delete_user/<int:UserID>', methods=['POST'])
def delete_user(UserID):
    # Call the function to delete the user based on UserID
    delete_user_by_id(UserID)

    # Flash a success message
    flash('User deleted successfully!', 'success')

    # Redirect back to the user management page
    return redirect('/admin/admin_user_management')

def delete_user_by_id(UserID):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Define the SQL query to delete the user
            sql = "DELETE FROM users WHERE UserID = %s"
            cursor.execute(sql, (UserID,))
            connection.commit()
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
    finally:
        if connection:
            connection.close()


@app.route('/admin/deactivate_user/<int:UserID>')
def deactivate_user(UserID):
    # Deactivate the user in the database (you'll need to implement this)
    deactivate_user_by_id(UserID)  # Replace with your own logic to deactivate users
    flash('User deactivated successfully!', 'success')
    return redirect('/admin/admin_user_management')

def get_reservation_details(reservation_id):
    try:
        connection = get_db_connection()  # Assuming you have a function to establish a database connection

        with connection.cursor() as cursor:
            # Retrieve reservation details based on the given reservation_id
            sql = "SELECT * FROM reservations WHERE id = %s"
            cursor.execute(sql, (reservation_id,))
            reservation = cursor.fetchone()
            return reservation  # Returns a dictionary of reservation details
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        return None  # Return None in case of an error
    finally:
        if connection:
            connection.close()

@app.route('/admin/admin_agent_management')
def admin_agent_management():
    # Get the category parameter from the URL
    category = request.args.get('category', 'pending')

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query agents based on the specified category
            if category == '':
                query = "SELECT * FROM agents WHERE ApprovalStatus = ''"
            elif category == 'pending':
                query = "SELECT * FROM agents WHERE ApprovalStatus = 'Pending'"
            elif category == 'approved':
                query = "SELECT * FROM agents WHERE ApprovalStatus = 'Approved'"
            elif category == 'declined':
                query = "SELECT * FROM agents WHERE ApprovalStatus = 'Declined'"
            else:
                # Handle invalid category parameter, e.g., show all agents
                query = "SELECT * FROM agents"
            
            cursor.execute(query)
            agents = cursor.fetchall()
    except pymysql.Error as e:
        # Handle any database errors and log them
        print(f"Database Error: {str(e)}")
        agents = []

    finally:
        connection.close()

    return render_template('/admin/admin_agent_management.html', agents=agents, category=category)
    
@app.route('/admin/approve_agent/<int:agent_id>', methods=['POST'])
def approve_agent(agent_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Update the agent's approval status to "Approved"
            update_query = "UPDATE agents SET ApprovalStatus = %s WHERE AgentID = %s"
            cursor.execute(update_query, ('Approved', agent_id))
            connection.commit()
            flash('Agent approved successfully!', 'success')
    except pymysql.Error as e:
        flash(f'Failed to approve agent. Error: {str(e)}', 'danger')
    finally:
        connection.close()
    
    return redirect('/admin/admin_agent_management')

@app.route('/admin/decline_agent/<int:agent_id>', methods=['POST'])
def decline_agent(agent_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Update the agent's approval status to "Declined"
            update_query = "UPDATE agents SET ApprovalStatus = %s WHERE AgentID = %s"
            cursor.execute(update_query, ('Declined', agent_id))
            connection.commit()
            flash('Agent declined successfully!', 'success')
    except pymysql.Error as e:
        flash(f'Failed to decline agent. Error: {str(e)}', 'danger')
    finally:
        connection.close()
    
    return redirect('/admin/admin_agent_management')

@app.route('/admin/delete_agent/<int:agent_id>', methods=['POST'])
def delete_agent(agent_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Delete the agent record from the database using the agent_id
            delete_query = "DELETE FROM agents WHERE AgentID = %s"
            cursor.execute(delete_query, (agent_id,))
            connection.commit()
            flash('Agent deleted successfully!', 'success')
    except pymysql.Error as e:
        flash(f'Failed to delete agent. Error: {str(e)}', 'danger')
    finally:
        connection.close()

    return redirect('/admin/admin_agent_management')

from flask import Flask, request, render_template, send_file, make_response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import pdfrw

import pdfrw
from pdfrw import PdfDict


@app.route('/input_data', methods=['GET', 'POST'])
def input_data():
    if request.method == 'POST':
        user_data = {
            'lastname': request.form['lastname'],
            'middlename': request.form['middlename'],
            'firstname': request.form['firstname'],
            'birthdate': request.form['birthdate'],
            'birthplace': request.form['birthplace'],
            'age': request.form['age'],
            'gender': request.form['gender'],
            'nationality': request.form['nationality'],
            'dependents': request.form['dependents'],
            'tin': request.form['tin'],
            'sss': request.form['sss'],
            'ctc': request.form['ctc'],
            'dateplaceissued': request.form['dateplaceissued'],
            'number_street': request.form['number_street'],
            'district_town': request.form['district_town'],
            'municipality_city': request.form['municipality_city'],
            'state_country': request.form['state_country'],
            'zip_code': request.form['zip_code'],
            'landline_phone': request.form['landline_phone'],
            'email': request.form['email'],
            'facebook_account': request.form['facebook_account'],
            'employer_name': request.form['employer_name'],
            'office_address': request.form['office_address'],
            'division_department': request.form['division_department'],
            'position': request.form['position'],
            'years_in_employment': request.form['years_in_employment'],
            'telephone_fax': request.form['telephone_fax'],
            'basic_salary': request.form['basic_salary'],
            'allowance_remuneration': request.form['allowance_remuneration'],
            'gross_income': request.form['gross_income'],
            'spouse_birthdate': request.form['spouse_birthdate'],
            'spouse_birthplace': request.form['spouse_birthplace'],
            'spouse_age': request.form['spouse_age'],
            'spouse_lastname': request.form['spouse_lastname'],
            'spouse_firstname': request.form['spouse_firstname'],
            'spouse_middle_name': request.form['spouse_middle_name'],
        
            'spouse_employer_name': request.form['spouse_employer_name'],
            'spouse_office_address': request.form['spouse_office_address'],
            'spouse_division_department': request.form['spouse_division_department'],
            'spouse_position': request.form['spouse_position'],
            'spouse_years_in_employment': request.form['spouse_years_in_employment'],
            'spouse_telephone_fax': request.form['spouse_telephone_fax'],
            'spouse_basic_salary': request.form['spouse_basic_salary'],
            'spouse_allowance_remuneration': request.form['spouse_allowance_remuneration'],
            'spouse_gross_income': request.form['spouse_gross_income'],
            'reference1_name': request.form['reference1_name'],
            'reference1_relationship': request.form['reference1_relationship'],
            'reference1_contact_no': request.form['reference1_contact_no'],
            'reference2_name': request.form['reference2_name'],
            'reference2_relationship': request.form['reference2_relationship'],
            'reference2_contact_no': request.form['reference2_contact_no'],
            'reference3_name': request.form['reference3_name'],
            'reference3_relationship': request.form['reference3_relationship'],
            'reference3_contact_no': request.form['reference3_contact_no'],
        
        }

        # Get the selected civil status value, default to blank
        selected_status = request.form.get('civilstatus', ' ')

        # Load the existing PDF template
        pdf_template = pdfrw.PdfReader('templates/reservform.pdf')

        for page in pdf_template.pages:
            annotations = page['/Annots']
            if annotations:
                for annotation in annotations:
                    if '/T' in annotation and '/V' in annotation:
                        field_name = annotation['/T'][1:-1]
                        if field_name in user_data:
                            annotation.update(pdfrw.PdfDict(V=user_data[field_name]))
                        elif field_name == 'civilstatus':
                            annotation.update(pdfrw.PdfDict(V=selected_status))

        # Save the filled-in PDF as a new file
        filled_pdf_filename = 'filled_template.pdf'
        pdfrw.PdfWriter().write(filled_pdf_filename, pdf_template)

        # Serve the filled-in PDF for download
        return send_file(filled_pdf_filename, as_attachment=True)

    return render_template('form.html')

if __name__ == '__main__':
    app.run(debug=True)
