from storage import app,os,commit
import mimetypes,fitz,io
from PIL import Image
from flask import render_template, redirect, url_for, flash, request, session, Response, send_file
from storage.modules import Repo,User
from storage.merkel_tree import MerkleTree,hashlib
from storage.forms import RegisterForm,LoginForm
from storage import db
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError  # Import for handling database integrity errors
from werkzeug.utils import secure_filename
from storage.commit import commitHistory
from datetime import datetime

def compute_file_hash(filepath):
  hasher = hashlib.sha256()
  with open(filepath,'rb') as f:
      buffer = f.read()
      hasher.update(buffer)
  return hasher.hexdigest()


@app.route("/")
@app.route("/home")
def home_page():
    return render_template("home.html")

@app.route("/login",methods=['GET','POST'])
def login_page():
    loginform=LoginForm()
    if(loginform.validate_on_submit()):
        attempted_user=User.query.filter_by(username=loginform.username.data).first()
        if attempted_user and attempted_user.check_password_correction(
            attempted_password=loginform.password.data
        ):
            login_user(attempted_user)
            flash(f'Successfully logged in as {attempted_user.username}',category='success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username and password does not match',category='danger')
            
    return render_template('login.html',form=loginform)

@app.route('/register',methods=['GET','POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user_to_create = User(username=form.username.data,
                              email_id=form.email_address.data,
                              password=form.password1.data)
        db.session.add(user_to_create)
        db.session.commit()
        login_user(user_to_create)
        flash(f"Account created successfully! You are now logged in as {user_to_create.username}", category='success')
        return redirect(url_for('dashboard'))
    if form.errors != {}: #If there are not errors from the validations
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a user: {err_msg}', category='danger')

    return render_template('register.html', form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("login_page"))

@app.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    user = User.query.get(current_user.id)

    # Handle repository creation
    if request.method == 'POST' and 'repo_name' in request.form:
        repo_name = request.form['repo_name'].strip().lower()
        visibility = request.form['visibility']
        is_private = (visibility == 'private')

        if repo_name:
            existing_repo = Repo.query.filter_by(reponame=repo_name, owner=user.id).first()
            if existing_repo:
                flash('A repository with this name already exists!', 'danger')
            else:
                try:
                    # Create a new empty Merkle Tree for the repo
                    merkle_tree = MerkleTree()
                    merkle_tree.build_tree([])  # Initially, no files
                    root_hash = merkle_tree.get_root_hash()

                    new_repo = Repo(
                        reponame=repo_name,
                        owner=user.id,
                        merkle_root=root_hash,
                        is_private=is_private
                    )
                    db.session.add(new_repo)
                    db.session.commit()
                    flash('Repository created successfully!', 'success')
                except IntegrityError:
                    db.session.rollback()
                    flash('A repository with this name already exists!', 'danger')
        else:
            flash('Repository name cannot be empty!', 'danger')

# Handle file uploads
    if request.method == 'POST' and 'file' in request.files:
        uploaded_files = request.files.getlist("file")  # Multiple files can be uploaded
        repo_id = request.form['repo_id']  # Repo ID from the form
        repo = Repo.query.get(repo_id)
        if repo and repo.owner == current_user.id:  # Use current_user to access the logged-in user
            file_hashes = []
            file_changes = {}

            for file in uploaded_files:
                if file:
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{repo.id}_{filename}")
                    file.save(filepath)

                    # Compute the file hash and append to file_hashes
                    file_hash = compute_file_hash(filepath)
                    file_hashes.append(file_hash)

                    # Record the file change (addition)
                    file_changes[filename] = 'added'

            if file_hashes:
                # Update the Merkle Tree with the new file hashes
                merkle_tree = MerkleTree()
                merkle_tree.build_tree(file_hashes)
                new_root_hash = merkle_tree.get_root_hash()

                # Update the repository's Merkle root
                repo.merkle_root = new_root_hash
                db.session.commit()

                commit_message = request.form.get("commit_message", "").strip()
                if not commit_message:
                    commit_message = f"Uploaded files to {repo.reponame}"

                # Add the commit with the message and file changes
                repo.commit_history.add_commit(commit_message, file_changes)
                flash('Files uploaded and Merkle tree updated!', 'success')
        else:
            flash('Repository not found or permission denied.', 'danger')


    # Fetch all the user's repositories
    repos = Repo.query.filter_by(owner=user.id).filter(Repo.forked_from.is_(None)).all()
    forked_repos = Repo.query.filter_by(owner=user.id).filter(Repo.forked_from.isnot(None)).all()
    public_repos = Repo.query.filter(
        Repo.is_private == False,
        Repo.owner != user.id  # Exclude user's own repositories
    ).all()

    # Handle search functionality
    query = request.args.get('query', '')
    if query:
        search_repo = Repo.query.filter(
            Repo.reponame.contains(query),
            Repo.is_private == False,
            Repo.owner != user.id  # Exclude user's own repositories from search
        ).all()
    else:
        search_repo = []

    return render_template(
        'dashboard.html',
        user=user,
        repos=repos,
        forked_repos=forked_repos,
        public_repos=public_repos,
        search_repos=search_repo
    )

@app.route('/repo/<int:repo_id>', methods=['GET', 'POST'])
@login_required
def repo_view(repo_id):
    repo = Repo.query.get_or_404(repo_id)

    upload_folder = app.config['UPLOAD_FOLDER']
    uploaded_files = os.listdir(upload_folder)

    repo_files = [file for file in uploaded_files if file.startswith(str(repo.id) + '_')]

    # Permission check for private repositories
    if repo.is_private and repo.owner != current_user.id:
        flash("Permission denied!", "danger")
        return redirect(url_for('dashboard'))

    # Handle repository deletion
    if request.method == "POST" and 'delete_repo' in request.form:
        if repo.owner == current_user.id:
            db.session.delete(repo)
            db.session.commit()
            flash("Repository deleted successfully!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Permission denied!", "danger")

    return render_template('repo.html', repo=repo, files=repo_files)


@app.route('/open_file/<filename>', methods=['GET'])
@login_required
def open_file(filename):
    # Define the path to the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Check if the file exists
    if not os.path.exists(file_path):
        return "File not found!", 404

    # Get the file extension
    _, file_extension = os.path.splitext(filename)
    
    # Handle PDF files
    if file_extension.lower() == '.pdf':
        with fitz.open(file_path) as pdf:
            # Extract text from each page in the PDF
            pdf_text = ""
            for page_num in range(pdf.page_count):
                page = pdf.load_page(page_num)
                pdf_text += page.get_text()

        return render_template('file_view.html', filename=filename, content=pdf_text)
    
    # Handle Image files
    elif file_extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        with open(file_path, 'rb') as img_file:
            image_data = img_file.read()
        
        # Return the image directly in the response
        return Response(image_data, mimetype=mimetypes.guess_type(file_path)[0])
    
    # Handle Code/Notebook files
    elif file_extension.lower() in ['.py', '.ipynb', '.txt', '.md','.c']:
        with open(file_path, 'r', encoding="utf-8") as file:
            file_content = file.read()
        
        return render_template('file_view.html', filename=filename, content=file_content)
    
    # Fallback for unsupported file types
    else:
        return "Unsupported file type!", 400
    
@app.route('/fork/<int:repo_id>',methods=['POST'])
@login_required
def fork_repo(repo_id):
    original_repo = Repo.query.get_or_404(repo_id)

    if original_repo.is_private:
        flash("Cannot fork a private repository","danger")
        return redirect(url_for('repo_view'),repo_id=repo_id)
    
    new_repo = Repo(
        reponame = f"{original_repo.reponame}-forked",
        owner = current_user.id,
        merkle_root = original_repo.merkle_root,
        forked_from = original_repo.id
    )

    db.session.add(new_repo)
    db.session.commit()

    flash(f"Repository {original_repo.reponame} forked successfully!",'success')
    return redirect(url_for('repo_view',repo_id=new_repo.id))

@app.route('/repo/<int:repo_id>/delete_file/<filename>', methods=['POST'])
@login_required
def delete_file(repo_id, filename):
    repo = Repo.query.get_or_404(repo_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        
        commit_message = f"Deleted file from {repo.reponame}"
        repo.commit_history.add_commit(commit_message)
        flash(f'{filename} deleted successfully!', 'success')
    else:
        flash(f'File {filename} not found!', 'danger')
    return redirect(url_for('repo_view', repo_id=repo_id))



@app.route('/show_commit_history/<int:repo_id>')
def show_commit_history(repo_id):
    repo = Repo.query.get_or_404(repo_id)
    print(f"Repo ID: {repo_id}, Commit History Head: {repo.commit_history.head}")
    if repo.commit_history and repo.commit_history.head:
        commit_history_list = []
        current_commit = repo.commit_history.head

        while current_commit:
            commit_history_list.append({
                "message": current_commit.message,
                "timestamp": current_commit.timestamp,
                "file_changes": current_commit.file_changes
            })
            current_commit = current_commit.next

        return render_template('commit_history.html', repo=repo, commit_history=commit_history_list)
    else:
        flash('No commit history found for this repository.', 'info')
        return redirect(url_for('repo_view', repo_id=repo_id))
