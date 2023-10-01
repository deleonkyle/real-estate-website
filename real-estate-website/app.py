from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import pymysql
from werkzeug.utils import secure_filename
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, redirect, url_for
import datetime
import random
import string



app = Flask(__name__)
app.secret_key = 'b1fd2e52903ba3d848b4ca718c9e2d2f08a94fa7d8721aa1'

db_host = 'localhost'
db_user = 'root'
db_password = 'root'
db_name = 'astra'

app.config['UPLOAD_FOLDER'] = 'static/uploads'

def get_db_connection():
    return pymysql.connect(host=db_host, user=db_user, password=db_password, database=db_name)

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/v_tour')
def v_tour():
    # Replace with your property data
    property_data = {
        'name': 'Property Name',
        'location': 'City, State',
        'price': '$1,000,000',
        'bedrooms': 3,
        'bathrooms': 2,
        'image_url': 'path/to/property-image.jpg'
    }
    return render_template('v_tour.html', property_data=property_data)

@app.route('/logout', methods=['GET'])
def logout():
    # Clear the user's session data
    session.clear()
    
    # Redirect to the login page or any other page after logout
    return redirect('/login')  # Replace '/login' with your login page URL

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

@app.route('/static/<filename>')
def uploaded_file(filename):
    return send_from_directory('/', filename)

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

@app.route('/property/<int:property_id>')
def property_details(property_id):
    # Fetch property details based on property_id
    property_details = get_property_details(property_id)  # Implement this function
    return render_template('property_details.html', property_details=property_details, property_id=property_id)

@app.route('/property/<int:property_id>/reserve', methods=['POST'])
def reserve_visit(property_id):
    if request.method == 'POST':
        client_name = request.form['client_name']
        client_email = request.form['client_email']
        client_number = request.form['client_number']
        visit_datetime = request.form['visit_datetime']

        # Check if the chosen reservation time is already reserved
        if is_time_slot_reserved(property_id, visit_datetime):
            flash('The chosen visit time is already reserved. Please choose another time.', 'danger')
        else:
            # Insert the visit reservation into the 'property_visits' table
            reservation_successful = reserve_property_visit(property_id, client_name, client_email, client_number, visit_datetime)

            if reservation_successful:
                flash('Visit reserved successfully!', 'success')
            else:
                flash('Failed to reserve visit. Please try again.', 'danger')

    # Redirect back to the property details page
    return redirect(url_for('property_details', property_id=property_id))

# Function to check if a time slot is already reserved
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

# Function to insert a visit reservation into the database
def reserve_property_visit(property_id, client_name, client_email, client_number, visit_datetime):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Insert the visit reservation into the 'property_visits' table
            sql = """
                INSERT INTO property_visits (PropertyID, ClientName, ClientEmail, ClientNumber, VisitDate, Status)
                VALUES (%s, %s, %s, %s, %s, 'Scheduled')
            """
            cursor.execute(sql, (property_id, client_name, client_email, client_number, visit_datetime))
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

@app.route('/virtual_tour')
def virtual_tour():
    return render_template('virtual_tour.html')

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
            one_month_ago = datetime.date.today() - datetime.timedelta(days=30)

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
        connection.close()  # Close the database connection when done

@app.route('/admin/add_property', methods=['GET', 'POST'])
def add_property():
    image_path = None  # Initialize image_path as None
    
    if request.method == 'POST':
        name = request.form['name']
        type = request.form['type']
        province = request.form['province']
        price = float(request.form['price'])
        beds = int(request.form['beds'])
        baths = int(request.form['baths'])
        sqft = int(request.form['sqft'])
        description = request.form['description']
        virtual_tour_url = request.form['virtual_tour_url']
        reserved = bool(request.form.get('reserved'))

       # Handle file upload
    if 'image' in request.files:
        image = request.files['image']
        if image.filename != '':
            # Securely save the uploaded image
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # You can save the filename to the database or process it further
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = """
                    INSERT INTO properties (name, type, province, price, beds, baths, sqft, description, virtual_tour_url, reserved, image_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (name, type, province, price, beds, baths, sqft, description, virtual_tour_url, reserved, image_path))
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

@app.route('/admin/edit_property/<int:property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        try:
            # Extract updated property data from the form
            name = request.form['name']
            property_type = request.form['type']
            province = request.form['province']
            price = request.form['price']
            beds = request.form['beds']
            toilet = request.form['toilet']
            baths = request.form['baths']
            sqft = request.form['sqft']
            description = request.form['description']
            virtual_tour_url = request.form['virtual_tour_url']
            reserved = request.form['reserved']

            # Check if an image file was uploaded
            if 'image_file' in request.files:
                image_file = request.files['image_file']
                if image_file.filename != '':
                    # Generate a secure filename and save the image to a folder
                    filename = secure_filename(image_file.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image_file.save(image_path)
                else:
                    image_path = None
            else:
                image_path = None

            # Update the property details in the database, including the image path
            sql = """UPDATE properties
                     SET name = %s, type = %s, province = %s, price = %s, beds = %s,
                         toilet = %s, baths = %s, sqft = %s, description = %s,
                         virtual_tour_url = %s, reserved = %s, image_path = %s
                     WHERE ListingID = %s"""

            cursor.execute(sql, (name, property_type, province, price, beds, toilet,
                                 baths, sqft, description, virtual_tour_url, reserved,
                                 image_path, property_id))

            connection.commit()  # Commit the changes to the database
            flash('Property updated successfully!', 'success')
            return redirect('/admin/properties')
        except Exception as e:
            connection.rollback()  # Rollback changes if an error occurs
            flash('An error occurred while updating the property.', 'danger')
            print(f"Error: {str(e)}")

    # Retrieve the property from the database using property_id
    cursor.execute("SELECT * FROM properties WHERE ListingID = %s", (property_id,))
    property = cursor.fetchone()

    connection.close()

    return render_template('/admin/edit_property.html', property=property)


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

        # Handle profile image upload
        profile_image = request.files.get('profile_image')
        if profile_image:
            # Save the uploaded file to a directory of your choice

        # Validate the form data (you can add more validation logic)
            if not username or not password or not email:
                flash('Username, password, and email are required fields.', 'danger')
            else:
                # Insert agent data into the database
                try:
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        # Replace 'agents' with your table name
                        insert_query = "INSERT INTO agents (Username, PasswordHash, Email, RealtyAffiliation, FirstName, LastName, DateOfBirth, PhoneNumber) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(insert_query, (username, password, email, realty_affiliation, first_name, last_name, date_of_birth, phone_number))
                        connection.commit()
                        flash('Registration successful!', 'success')
                except Exception as e:
                    flash(f'Registration failed. Error: {e}', 'danger')
                finally:
                    connection.close()

            return redirect(url_for('agent_registration'))

    return render_template('agent_registration.html')


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
    house_type = request.form.get('type')
        
    query = "SELECT * FROM properties WHERE 1=1"
    parameters = []

    if province:
        query += " AND province = %s"
        parameters.append(province)
    if house_type:
        query += " AND type = %s"
        parameters.append(house_type)

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

# Registration route
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

        # Hash the password
        password_hash = generate_password_hash(password)

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


# Login route
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
                    email = user[3]
                    user_type = user[4]
                    
                    if check_password_hash(password_hash, password):
                        session['user_id'] = user_id
                        flash('Login successful!', 'success')
                        
                        # Redirect users to their respective dashboards based on user_type
                        if user_type == 'admin':
                            return redirect(url_for('admin_dashboard'))
                        elif user_type == 'manager':
                            return redirect(url_for('manager_dashboard'))
                        elif user_type == 'agent':
                            return redirect(url_for('agent_dashboard'))
                        else:
                            # Handle other user types or roles accordingly
                            return redirect(url_for('dashboard'))  # Default dashboard
                        
                    else:
                        flash('Invalid password', 'danger')
                else:
                    flash('Invalid username', 'danger')
        except pymysql.Error as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            connection.close()

    return render_template('login.html')

@app.route('/agent/agent_dashboard')
def agent_dashboard():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Retrieve the total number of properties
            cursor.execute("SELECT COUNT(*) FROM properties")
            total_properties = cursor.fetchone()[0]

            # Retrieve the agent's username
            cursor.execute("SELECT Username FROM users WHERE UserType = 'agent' LIMIT 1")
            agent_username = cursor.fetchone()[0]
    except pymysql.Error as e:
        flash(f"Error: {str(e)}", 'danger')
        total_properties = 0
        agent_username = ""
    finally:
        connection.close()

    return render_template('/agent/agent_dashboard.html', total_properties=total_properties, agent_username=agent_username)



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

if __name__ == '__main__':
    app.run(debug=True)
