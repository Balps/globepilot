# 🚀 GlobePiloT Deployment Guide

This guide covers deploying GlobePiloT to your domain **myglobepilot.com**.

## 📋 Prerequisites

- Domain: `myglobepilot.com` (✅ You have this!)
- OpenAI API Key
- Tavily API Key
- Cloud hosting account (see options below)

## 🌐 Deployment Options

### Option 1: DigitalOcean App Platform (Recommended) 💰 ~$5/month

**Why DigitalOcean:**
- Easy deployment from GitHub
- Automatic SSL certificates
- Built-in domain management
- Affordable pricing

**Steps:**
1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit for myglobepilot.com"
   git branch -M main
   git remote add origin https://github.com/yourusername/globepilot.git
   git push -u origin main
   ```

2. **Deploy on DigitalOcean:**
   - Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
   - Click "Create App"
   - Connect your GitHub repository
   - Choose "Web Service"
   - Set build command: `pip install -r requirements.txt`
   - Set run command: `gunicorn --bind 0.0.0.0:8080 wsgi:app`
   - Add environment variables:
     - `OPENAI_API_KEY`: your-openai-key
     - `TAVILY_API_KEY`: your-tavily-key
     - `SECRET_KEY`: generate-random-string
     - `FLASK_ENV`: production

3. **Connect Domain:**
   - In App settings, add custom domain: `myglobepilot.com`
   - Update GoDaddy DNS:
     - Add CNAME record: `@` → `your-app.ondigitalocean.app`
     - Add CNAME record: `www` → `your-app.ondigitalocean.app`

### Option 2: Railway 💰 ~$5/month

**Steps:**
1. Push code to GitHub (same as above)
2. Go to [Railway.app](https://railway.app)
3. Connect GitHub repo
4. Add environment variables
5. Deploy automatically
6. Connect custom domain in Railway dashboard

### Option 3: Heroku 💰 ~$7/month

**Steps:**
1. Create `Procfile`:
   ```
   web: gunicorn wsgi:app
   ```
2. Deploy to Heroku
3. Add environment variables in Heroku dashboard
4. Connect domain in Heroku settings

### Option 4: Docker + VPS (Advanced) 💰 ~$5-20/month

**For experienced users with VPS (DigitalOcean Droplet, AWS EC2, etc.):**

1. **Server Setup:**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Install Docker Compose
   sudo apt-get install docker-compose
   ```

2. **Deploy:**
   ```bash
   # Clone your repo on server
   git clone https://github.com/yourusername/globepilot.git
   cd globepilot
   
   # Set environment variables
   export OPENAI_API_KEY="your-key"
   export TAVILY_API_KEY="your-key"
   export SECRET_KEY="your-secret"
   
   # Build and run
   docker-compose up -d
   ```

3. **Nginx Setup:**
   ```nginx
   server {
       listen 80;
       server_name myglobepilot.com www.myglobepilot.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## 🔧 Environment Variables

Set these in your hosting platform:

```
OPENAI_API_KEY=sk-your-openai-api-key
TAVILY_API_KEY=tvly-your-tavily-api-key
SECRET_KEY=generate-a-random-secret-key
FLASK_ENV=production
PORT=8000
```

## 🌍 Domain Configuration (GoDaddy)

1. **Login to GoDaddy DNS Management**
2. **Add DNS Records:**
   
   **For DigitalOcean/Railway/Heroku:**
   ```
   Type: CNAME
   Name: @
   Value: your-app-url.platform.com
   TTL: 1 Hour
   
   Type: CNAME  
   Name: www
   Value: your-app-url.platform.com
   TTL: 1 Hour
   ```
   
   **For VPS with IP address:**
   ```
   Type: A
   Name: @
   Value: your.server.ip.address
   TTL: 1 Hour
   
   Type: A
   Name: www  
   Value: your.server.ip.address
   TTL: 1 Hour
   ```

## ✅ Verification

After deployment:

1. **Test URLs:**
   - http://myglobepilot.com
   - http://www.myglobepilot.com
   - https://myglobepilot.com (SSL should auto-configure)

2. **Test Functionality:**
   - Create a test travel plan
   - Verify all 11 AI agents work
   - Test revision system
   - Check packing and document suggestions

## 🚨 Security Checklist

- ✅ API keys stored as environment variables
- ✅ SECRET_KEY set to random value
- ✅ FLASK_ENV=production
- ✅ Debug mode disabled
- ✅ HTTPS enabled (automatic with most platforms)

## 📞 Recommended: DigitalOcean

**Best option for myglobepilot.com:**
- $5/month starter plan
- Easy GitHub integration  
- Automatic SSL
- Built-in domain management
- Good performance for AI workloads

**Quick Start:**
1. Sign up at [DigitalOcean](https://m.do.co/c/your-referral)
2. Create app from GitHub
3. Add environment variables
4. Connect myglobepilot.com
5. Launch! 🚀

---

Need help with deployment? The community can assist with specific platform questions! 