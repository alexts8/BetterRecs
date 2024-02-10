@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    file_path = ".cache"
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect("https://accounts.spotify.com/en/logout")