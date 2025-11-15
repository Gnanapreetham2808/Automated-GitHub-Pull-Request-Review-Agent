# Frontend User Guide

## 🎨 **Beautiful Web Interface**

Your PR Review Agent now includes a modern, responsive web UI!

### 🌟 **Features**

- **Clean Design** - Modern gradient hero, smooth animations
- **Two Review Modes**
  - Manual Diff: Paste any git diff directly
  - GitHub PR: Enter owner/repo/PR number
- **Real-time Results** - Live updates with loading states
- **Smart Categorization** - Issues organized by type (Logic, Style, Security, Performance)
- **Confidence Scores** - Each comment includes AI confidence level
- **Summary Generation** - AI-powered overview of findings
- **Responsive Design** - Works on desktop, tablet, and mobile

---

## 🚀 **How to Use**

### 1. Start the Server

```powershell
uvicorn app:app --reload
```

### 2. Open Your Browser

Navigate to: **http://localhost:8000**

### 3. Choose Your Review Method

#### **Option A: Manual Diff**
1. Click on "Manual Diff" tab
2. Paste your git diff into the text area
3. Click "Analyze Diff"
4. Wait for AI analysis (10-30 seconds)
5. View results with detailed comments

#### **Option B: GitHub PR**
1. Click on "GitHub PR" tab
2. Enter:
   - Repository Owner (e.g., `facebook`)
   - Repository Name (e.g., `react`)
   - PR Number (e.g., `12345`)
3. Click "Review PR"
4. AI will fetch and analyze the PR
5. View comprehensive review results

---

## 📊 **Understanding Results**

### **Summary Card**
- High-level overview of all issues found
- AI-generated summary of critical findings

### **Statistics Dashboard**
- Total Issues count
- Breakdown by category:
  - 🧠 **Logic** - Correctness issues
  - ✨ **Style** - Code quality issues
  - 🔒 **Security** - Vulnerabilities
  - ⚡ **Performance** - Optimization opportunities

### **Comment Cards**
Each issue shows:
- **Category Badge** - Color-coded by type
- **File Location** - Path and line number
- **Confidence Score** - How confident the AI is (High/Medium/Low)
- **Detailed Description** - Explanation of the issue

---

## 🎨 **Color Coding**

- **Purple** 🟣 - Logic issues
- **Cyan** 🔵 - Style issues
- **Red** 🔴 - Security issues
- **Orange** 🟠 - Performance issues

### Confidence Levels
- **Green** 🟢 - High confidence (80-100%)
- **Orange** 🟠 - Medium confidence (50-79%)
- **Gray** ⚪ - Low confidence (0-49%)

---

## 💡 **Tips for Best Results**

### For Manual Diffs:
- Use `git diff` command to generate diffs
- Include context lines for better analysis
- Smaller diffs = faster analysis

### For GitHub PRs:
- Make sure GITHUB_TOKEN is configured in `.env`
- Public repos work without authentication
- Private repos require token with `repo` scope

### Performance:
- Large PRs may take 30-60 seconds
- The system processes 4 agents concurrently
- Timeout is set to 120 seconds

---

## 🔧 **Troubleshooting**

### "Failed to analyze diff"
- Check if diff format is valid
- Ensure it's a unified diff (from `git diff`)

### "GitHub API error"
- Verify GITHUB_TOKEN in `.env` file
- Check if PR number exists
- Confirm repo owner/name spelling

### "Request timed out"
- PR might be too large
- Try analyzing files individually
- Check network connection

### UI not loading
- Ensure server is running (`uvicorn app:app --reload`)
- Clear browser cache
- Check browser console for errors

---

## 🎯 **Example Use Cases**

### 1. **Pre-commit Review**
```bash
# Generate diff of your changes
git diff > my-changes.diff

# Paste into Manual Diff tab
# Review AI feedback before committing
```

### 2. **PR Review Automation**
- Enter PR details in GitHub PR tab
- Get comprehensive review in seconds
- Share results with team

### 3. **Code Quality Checks**
- Regular reviews of feature branches
- Security audits of changes
- Performance optimization suggestions

---

## 📱 **Mobile Support**

The UI is fully responsive and works on:
- 📱 Mobile phones
- 📱 Tablets
- 💻 Laptops
- 🖥️ Desktops

---

## 🌐 **Browser Support**

Tested and works on:
- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Opera

---

## 🎨 **Customization**

### Changing Colors
Edit `static/css/style.css`:
```css
:root {
    --primary: #667eea;  /* Change primary color */
    --secondary: #764ba2; /* Change secondary color */
}
```

### Modifying Layout
Edit `templates/index.html` to adjust structure

### Adding Features
Edit `static/js/app.js` for new functionality

---

## 📸 **Screenshots**

### Hero Section
- Beautiful gradient background
- Clear call-to-action buttons
- Feature highlights

### Review Interface
- Tabbed interface (Manual/GitHub)
- Clean form inputs
- Real-time loading states

### Results Display
- Summary card with AI insights
- Statistics dashboard
- Detailed comment cards

---

## 🚀 **Next Steps**

1. ✅ Review some code using the UI
2. ✅ Check the API docs at `/docs`
3. ✅ Customize colors to match your brand
4. ✅ Deploy to production
5. ✅ Share with your team

---

## 💬 **Feedback**

The UI is designed to be:
- **Intuitive** - No learning curve
- **Fast** - Optimized performance
- **Beautiful** - Modern design
- **Functional** - All features accessible

Enjoy your new AI-powered code review interface! 🎉
