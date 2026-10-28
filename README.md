# 💰 Personal Expense Tracker

A clean, modern, and beginner-friendly web application to track your everyday personal expenses. Built with standard **HTML5, CSS3, and vanilla JavaScript** without requiring any frameworks, external databases, or paid API keys.

---

## ✨ Features

- **Intuitive & Responsive UI**: Works seamlessly across desktops, tablets, and mobile screens.
- **Add Expenses Easily**: Record each expense with a description, amount, category, and date.
- **Formatted Table View**: Lists all transactions with formatted currency (`$XX.XX`), human-readable dates, and color-coded category badges.
- **Live Summary Metrics**: Automatically calculates and displays total spending and transaction count.
- **Delete Functionality**: Remove any individual expense with a confirmation prompt.
- **Browser Persistence**: All your data is saved in your browser's `localStorage`, so your records remain intact even after refreshing the page or restarting your browser.
- **Safe & Private**: 100% client-side. No accounts, backend servers, or third-party tracking required.

---

## 📁 File Structure

The project is structured into three simple, cleanly organized files:

```text
├── index.html   # The markup structure: semantic headers, cards, form inputs, and table
├── styles.css   # Clean, modern styling: CSS variables, flexbox, grid, and responsive design
├── app.js       # The application logic: localStorage management, calculations, validation, and rendering
└── README.md    # Documentation and local setup instructions
```

---

## 🚀 How to Run the Application Locally

You can run this application in seconds using any of the following methods:

### Method 1: Direct Browser Open (Easiest)

1. Open your computer's file explorer (Finder on macOS or File Explorer on Windows).
2. Navigate to the project folder (`Antigravity`).
3. Double-click **`index.html`** (or right-click and choose **Open With > Google Chrome / Safari / Edge / Firefox**).
4. That's it! The application is running immediately.

---

### Method 2: Using Python's Built-in Local Web Server

If you prefer running with a local HTTP server:

1. Open your terminal in this directory:
   ```bash
   cd /Users/sirigogineni/Documents/Antigravity
   ```
2. Start the local server:
   ```bash
   python3 -m http.server 8000
   ```
3. Open your browser and visit:
   ```text
   http://localhost:8000
   ```

---

## 🛠️ How It Works (For Beginners)

1. **HTML (`index.html`)**:
   - Defines the visual elements: input fields for description, amount, category, and date, as well as the summary cards and the table where expenses are listed.

2. **CSS (`styles.css`)**:
   - Uses **CSS Variables** (`:root`) for easy theming (colors, borders, fonts).
   - Implements **CSS Grid** and **Flexbox** for a responsive layout that automatically adjusts between desktop and mobile devices.

3. **JavaScript (`app.js`)**:
   - **`localStorage`**: Stores data in key-value format inside the browser. Data is converted to a text string with `JSON.stringify()` when saved, and converted back to an array with `JSON.parse()` when loaded.
   - **Form Validation**: Checks that numbers are positive, text is not blank, and dates are chosen before adding to the list.
   - **Dynamic Rendering**: Clears and re-builds the `<tbody>` rows whenever an item is added or deleted, and recalculates the total spent using JavaScript's `.reduce()` method.
