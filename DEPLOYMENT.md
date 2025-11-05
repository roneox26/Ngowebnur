# Deployment Guide

## Railway Deployment (Recommended - Free & Easy)

### Steps:

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Deploy Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Add MySQL Database**
   - Click "New" → "Database" → "Add MySQL"
   - Railway automatically sets DATABASE_URL

4. **Environment Variables** (Optional)
   - Add SECRET_KEY if needed

5. **Deploy**
   - Railway automatically deploys
   - Your app will be live at: `your-app.railway.app`

### Local Testing with MySQL:
```bash
# Install dependencies
pip install -r requirements.txt

# Set MySQL connection
set DATABASE_URL=mysql://user:password@host:3306/dbname

# Run app
python app.py
```

## Alternative: Render + PostgreSQL (Free)

1. Go to https://render.com
2. Create Web Service from GitHub
3. Add PostgreSQL database (free)
4. Deploy

## Alternative: PythonAnywhere (Free)

1. Upload files to PythonAnywhere
2. Uses SQLite (persistent storage)
3. Configure WSGI
4. No database setup needed

## Note:
- **Vercel**: ❌ Not suitable (no persistent storage for SQLite)
- **Railway**: ✅ Best option (free MySQL + persistent)
- **Render**: ✅ Good option (free PostgreSQL)
- **PythonAnywhere**: ✅ Simple option (SQLite works)
