/* ==========================================================================
   Personal Expense Tracker - Simple, Clean JavaScript Logic
   ========================================================================== */

// --- 1. DOM Element Selectors ---
// We grab references to all the HTML elements we need to interact with.
const expenseForm = document.getElementById('expenseForm');
const descriptionInput = document.getElementById('description');
const amountInput = document.getElementById('amount');
const categorySelect = document.getElementById('category');
const dateInput = document.getElementById('date');

const expenseTable = document.getElementById('expenseTable');
const expenseList = document.getElementById('expenseList');
const emptyState = document.getElementById('emptyState');
const totalAmountDisplay = document.getElementById('totalAmount');
const totalCountDisplay = document.getElementById('totalCount');
const expenseCounterBadge = document.getElementById('expenseCounter');

// Error message elements
const descError = document.getElementById('descError');
const amountError = document.getElementById('amountError');
const catError = document.getElementById('catError');
const dateError = document.getElementById('dateError');

// Storage key for LocalStorage
const STORAGE_KEY = 'personal_expenses_data';

// --- 2. Application State ---
// This array will hold all of our expense objects in memory.
let expenses = [];

// Sample starter data shown only on the very first visit
const DEFAULT_SAMPLE_DATA = [
  {
    id: '1',
    description: 'Weekly Grocery Run',
    amount: 64.50,
    category: 'Food & Dining',
    date: getTodayDateString()
  },
  {
    id: '2',
    description: 'Subway Monthly Pass',
    amount: 32.00,
    category: 'Transportation',
    date: getTodayDateString()
  },
  {
    id: '3',
    description: 'Movie Night Tickets',
    amount: 18.75,
    category: 'Entertainment',
    date: getTodayDateString()
  }
];

// --- 3. Helper Functions ---

/**
 * Returns today's date formatted as YYYY-MM-DD for <input type="date">.
 */
function getTodayDateString() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Formats a number into a clean USD currency string (e.g. $1,234.56).
 * @param {number} value
 * @returns {string}
 */
function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value || 0);
}

/**
 * Formats a YYYY-MM-DD date string into a friendly, readable format (e.g., "Oct 28, 2026").
 * @param {string} dateStr
 * @returns {string}
 */
function formatDate(dateStr) {
  if (!dateStr) return '';
  const [year, month, day] = dateStr.split('-');
  if (!year || !month || !day) return dateStr;
  
  const dateObj = new Date(year, month - 1, day);
  return dateObj.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

/**
 * Loads expenses from the browser's localStorage.
 * If visiting for the first time, loads default sample data.
 */
function loadExpensesFromStorage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === null) {
      // First-time visit: provide helpful starter expenses
      expenses = [...DEFAULT_SAMPLE_DATA];
      saveExpensesToStorage();
    } else {
      expenses = JSON.parse(stored) || [];
    }
  } catch (error) {
    console.error('Error reading expenses from localStorage:', error);
    expenses = [];
  }
}

/**
 * Saves current expenses array into localStorage as a JSON string.
 */
function saveExpensesToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(expenses));
  } catch (error) {
    console.error('Error saving expenses to localStorage:', error);
  }
}

// --- 4. Render Functions ---

/**
 * Calculates the total sum of all expenses.
 * @returns {number}
 */
function calculateTotalSpent() {
  return expenses.reduce((total, expense) => total + (Number(expense.amount) || 0), 0);
}

/**
 * Renders the table rows, updates total amount, transaction counts,
 * and toggles the empty state view.
 */
function renderExpenses() {
  // Clear any existing table rows
  expenseList.innerHTML = '';

  // Update Summary Counts
  const totalSpent = calculateTotalSpent();
  totalAmountDisplay.textContent = formatCurrency(totalSpent);
  totalCountDisplay.textContent = expenses.length.toString();
  expenseCounterBadge.textContent = `${expenses.length} ${expenses.length === 1 ? 'record' : 'records'}`;

  // If there are no expenses, display the empty state message
  if (expenses.length === 0) {
    emptyState.style.display = 'block';
    expenseTable.style.display = 'none';
    return;
  }

  // Show table and hide empty state
  emptyState.style.display = 'none';
  expenseTable.style.display = 'table';

  // Build table rows
  expenses.forEach((expense) => {
    const row = document.createElement('tr');

    row.innerHTML = `
      <td class="expense-date">${escapeHTML(formatDate(expense.date))}</td>
      <td class="expense-desc">${escapeHTML(expense.description)}</td>
      <td>
        <span class="category-badge" data-cat="${escapeHTML(expense.category)}">
          ${escapeHTML(expense.category)}
        </span>
      </td>
      <td class="expense-amount text-right">${formatCurrency(expense.amount)}</td>
      <td class="text-center">
        <button 
          class="btn-delete" 
          type="button"
          data-id="${escapeHTML(expense.id)}"
          title="Delete expense"
          aria-label="Delete ${escapeHTML(expense.description)}"
        >
          🗑️ Delete
        </button>
      </td>
    `;

    expenseList.appendChild(row);
  });
}

/**
 * Simple sanitizer to prevent HTML injection in user input.
 * @param {string} str
 * @returns {string}
 */
function escapeHTML(str) {
  if (typeof str !== 'string') return str;
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// --- 5. Form Validation & Handling ---

/**
 * Validates form inputs and displays clear error messages if invalid.
 * @returns {boolean} True if form is valid, false otherwise.
 */
function validateForm() {
  let isValid = true;

  // Validate Description
  const description = descriptionInput.value.trim();
  if (!description) {
    showFieldError(descriptionInput, descError, 'Please enter a description.');
    isValid = false;
  } else {
    clearFieldError(descriptionInput, descError);
  }

  // Validate Amount
  const amountVal = parseFloat(amountInput.value);
  if (isNaN(amountVal) || amountVal <= 0) {
    showFieldError(amountInput, amountError, 'Please enter an amount greater than 0.');
    isValid = false;
  } else {
    clearFieldError(amountInput, amountError);
  }

  // Validate Category
  if (!categorySelect.value) {
    showFieldError(categorySelect, catError, 'Please select a category.');
    isValid = false;
  } else {
    clearFieldError(categorySelect, catError);
  }

  // Validate Date
  if (!dateInput.value) {
    showFieldError(dateInput, dateError, 'Please select a date.');
    isValid = false;
  } else {
    clearFieldError(dateInput, dateError);
  }

  return isValid;
}

function showFieldError(inputElement, errorElement, message) {
  inputElement.classList.add('invalid');
  errorElement.textContent = message;
  errorElement.classList.add('visible');
}

function clearFieldError(inputElement, errorElement) {
  inputElement.classList.remove('invalid');
  errorElement.classList.remove('visible');
}

/**
 * Handles the "Add Expense" form submission.
 * @param {Event} e
 */
function handleAddExpense(e) {
  e.preventDefault();

  if (!validateForm()) {
    return;
  }

  // Create new expense object
  const newExpense = {
    id: Date.now().toString(), // Simple unique ID using timestamp
    description: descriptionInput.value.trim(),
    amount: parseFloat(parseFloat(amountInput.value).toFixed(2)),
    category: categorySelect.value,
    date: dateInput.value
  };

  // Add the new expense to the start of our list
  expenses.unshift(newExpense);

  // Persist to localStorage
  saveExpensesToStorage();

  // Re-render UI
  renderExpenses();

  // Reset form inputs & restore today's date
  expenseForm.reset();
  dateInput.value = getTodayDateString();

  // Focus description for fast subsequent entries
  descriptionInput.focus();
}

/**
 * Deletes an expense by its unique ID.
 * @param {string} id
 */
function handleDeleteExpense(id) {
  const expenseToDelete = expenses.find((item) => item.id === id);
  const desc = expenseToDelete ? `"${expenseToDelete.description}"` : 'this expense';

  const confirmed = window.confirm(`Are you sure you want to delete ${desc}?`);
  if (!confirmed) return;

  // Filter out the selected expense
  expenses = expenses.filter((item) => item.id !== id);

  // Save updated list & update UI
  saveExpensesToStorage();
  renderExpenses();
}

// --- 6. Event Listeners & Initialization ---

// Event delegation for delete buttons
expenseList.addEventListener('click', (e) => {
  const deleteBtn = e.target.closest('.btn-delete');
  if (deleteBtn) {
    const id = deleteBtn.getAttribute('data-id');
    if (id) {
      handleDeleteExpense(id);
    }
  }
});

// Real-time error clearing when user types or changes fields
descriptionInput.addEventListener('input', () => {
  if (descriptionInput.value.trim()) clearFieldError(descriptionInput, descError);
});

amountInput.addEventListener('input', () => {
  if (parseFloat(amountInput.value) > 0) clearFieldError(amountInput, amountError);
});

categorySelect.addEventListener('change', () => {
  if (categorySelect.value) clearFieldError(categorySelect, catError);
});

dateInput.addEventListener('change', () => {
  if (dateInput.value) clearFieldError(dateInput, dateError);
});

// Form submit event listener
expenseForm.addEventListener('submit', handleAddExpense);

/**
 * Application bootstrapper.
 */
function initApp() {
  // Set default date to today
  dateInput.value = getTodayDateString();

  // Load saved expenses (or defaults) from localStorage
  loadExpensesFromStorage();

  // Render the initial UI
  renderExpenses();
}

// Run app once DOM is ready
document.addEventListener('DOMContentLoaded', initApp);
