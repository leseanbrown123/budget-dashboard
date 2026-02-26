/* ===== Budget Dashboard Frontend ===== */

const CATEGORIES = [
    "Groceries", "Dining", "Food Delivery", "Transportation", "Shopping",
    "Entertainment", "Utilities", "Healthcare", "Travel", "Subscriptions",
    "Education", "Personal Care", "Home", "Insurance", "Other"
];

const CATEGORY_COLORS = {
    "Groceries": "#00b894",
    "Dining": "#e17055",
    "Food Delivery": "#ff7675",
    "Transportation": "#0984e3",
    "Shopping": "#6c5ce7",
    "Entertainment": "#fdcb6e",
    "Utilities": "#636e72",
    "Healthcare": "#e84393",
    "Travel": "#00cec9",
    "Subscriptions": "#a29bfe",
    "Education": "#55efc4",
    "Personal Care": "#fab1a0",
    "Home": "#74b9ff",
    "Insurance": "#81ecec",
    "Other": "#b2bec3",
};

const REC_ICONS = {
    "success": "\u2705",
    "warning": "\u26a0\ufe0f",
    "danger": "\ud83d\udea8",
    "info": "\ud83d\udca1",
};

let categoryChart = null;
let bucketChart = null;
let lastAnalysisParams = null;
let allTransactions = [];

/* ===== File Upload ===== */

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFiles(files);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) uploadFiles(fileInput.files);
});

async function uploadFiles(fileList) {
    const status = document.getElementById("upload-status");
    const files = Array.from(fileList);
    const total = files.length;
    let successCount = 0;
    let errorMessages = [];
    let lastData = null;

    status.hidden = false;
    status.className = "status-msg";
    status.textContent = `Uploading ${total} file${total > 1 ? "s" : ""}...`;

    for (const file of files) {
        if (total > 1) {
            status.textContent = `Uploading ${file.name} (${successCount + 1}/${total})...`;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/upload", { method: "POST", body: formData });
            const data = await res.json();

            if (res.ok) {
                successCount++;
                lastData = data;
            } else {
                errorMessages.push(`${file.name}: ${data.error || "Upload failed"}`);
            }
        } catch (err) {
            errorMessages.push(`${file.name}: Network error`);
        }
    }

    if (successCount > 0 && lastData) {
        document.getElementById("clear-btn").hidden = false;
        renderTransactions(lastData.transactions);
    }

    if (errorMessages.length === 0) {
        status.className = "status-msg success";
        status.textContent = `Uploaded ${successCount} file${successCount > 1 ? "s" : ""}. Total transactions: ${lastData.total_count}`;
    } else if (successCount > 0) {
        status.className = "status-msg warning";
        status.textContent = `Uploaded ${successCount}/${total} files (${lastData.total_count} transactions). Errors: ${errorMessages.join("; ")}`;
    } else {
        status.className = "status-msg error";
        status.textContent = errorMessages.join("; ");
    }

    // Reset so the same files can be re-uploaded
    fileInput.value = "";
}

async function clearData() {
    await fetch("/clear", { method: "POST" });
    document.getElementById("upload-status").hidden = true;
    document.getElementById("clear-btn").hidden = true;
    document.getElementById("transactions-section").hidden = true;
    document.getElementById("results-section").hidden = true;
    document.getElementById("transactions-month-select").value = "all";
    allTransactions = [];
}

/* ===== Transactions Table ===== */

function renderTransactions(transactions) {
    allTransactions = transactions;

    // Populate month filter dropdown
    const months = [...new Set(
        transactions
            .filter(t => t.date && t.date.length >= 7)
            .map(t => t.date.substring(0, 7))
    )].sort();

    const monthSelect = document.getElementById("transactions-month-select");
    const currentValue = monthSelect.value || "all";
    monthSelect.innerHTML = `<option value="all">All Months</option>`;
    months.forEach(m => {
        const [year, mo] = m.split("-");
        const label = new Date(year, parseInt(mo) - 1).toLocaleString("default", { month: "long", year: "numeric" });
        monthSelect.innerHTML += `<option value="${m}" ${currentValue === m ? "selected" : ""}>${label}</option>`;
    });

    filterTransactionsByMonth(currentValue);
}

function filterTransactionsByMonth(month) {
    const section = document.getElementById("transactions-section");
    section.hidden = false;
    const tbody = section.querySelector("tbody");
    tbody.innerHTML = "";

    const filtered = month === "all"
        ? allTransactions
        : allTransactions.filter(t => t.date && t.date.startsWith(month));

    filtered.forEach((t) => {
        // Find the original index in allTransactions for category updates
        const originalIndex = allTransactions.indexOf(t);
        const tr = document.createElement("tr");
        if (t.flagged) tr.style.background = "#fff3e0";

        const flagMarker = t.flagged ? ' <span class="flag-icon">[!]</span>' : "";

        tr.innerHTML = `
            <td>${t.date}</td>
            <td>${escapeHtml(t.description)}${flagMarker}</td>
            <td class="amount">$${t.amount.toFixed(2)}</td>
            <td>
                <select class="category-select" data-index="${originalIndex}" onchange="updateCategory(this)">
                    ${CATEGORIES.map(c =>
                        `<option value="${c}" ${c === t.category ? "selected" : ""}>${c}</option>`
                    ).join("")}
                </select>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function updateCategory(select) {
    const index = parseInt(select.dataset.index);
    const category = select.value;

    try {
        await fetch("/update-category", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ index, category }),
        });
    } catch (err) {
        console.error("Failed to update category:", err);
    }
}

/* ===== Analysis ===== */

async function runAnalysis(month) {
    const income = document.getElementById("income-input").value;
    const goalsText = document.getElementById("goals-input").value;

    if (!income || parseFloat(income) <= 0) {
        alert("Please enter your monthly take-home income.");
        return;
    }

    const goals = goalsText
        .split("\n")
        .map(g => g.trim())
        .filter(g => g.length > 0);

    const selectedMonth = month || "all";

    lastAnalysisParams = { income: parseFloat(income), goals };

    try {
        const res = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ income: parseFloat(income), goals, month: selectedMonth }),
        });
        const data = await res.json();

        if (res.ok) {
            renderResults(data);
        } else {
            alert(data.error || "Analysis failed");
        }
    } catch (err) {
        alert("Network error. Is the server running?");
    }
}

async function switchMonth(month) {
    if (!lastAnalysisParams) return;
    await runAnalysis(month);
}

function renderResults(data) {
    const section = document.getElementById("results-section");
    section.hidden = false;
    section.scrollIntoView({ behavior: "smooth" });

    // Month picker
    const monthPicker = document.getElementById("month-picker");
    if (data.available_months && data.available_months.length > 0) {
        monthPicker.hidden = false;
        const monthSelect = document.getElementById("month-select");
        const currentValue = data.selected_month || "all";
        monthSelect.innerHTML = `<option value="all" ${currentValue === "all" ? "selected" : ""}>All Months</option>`;
        data.available_months.forEach(m => {
            const [year, mo] = m.split("-");
            const label = new Date(year, parseInt(mo) - 1).toLocaleString("default", { month: "long", year: "numeric" });
            monthSelect.innerHTML += `<option value="${m}" ${currentValue === m ? "selected" : ""}>${label}</option>`;
        });
    } else {
        monthPicker.hidden = true;
    }

    // Summary cards
    const summaryRow = document.getElementById("summary-cards");
    const spendClass = data.spending_pct > 90 ? "danger" : data.spending_pct > 80 ? "warning" : "success";
    summaryRow.innerHTML = `
        <div class="summary-card">
            <div class="label">Monthly Income</div>
            <div class="value">$${data.monthly_income.toLocaleString()}</div>
        </div>
        <div class="summary-card">
            <div class="label">Total Spending</div>
            <div class="value ${spendClass}">$${data.total_spending.toLocaleString()}</div>
        </div>
        <div class="summary-card">
            <div class="label">Remaining</div>
            <div class="value ${data.remaining >= 0 ? 'success' : 'danger'}">$${data.remaining.toLocaleString()}</div>
        </div>
        <div class="summary-card">
            <div class="label">Spending Rate</div>
            <div class="value ${spendClass}">${data.spending_pct}%</div>
        </div>
    `;

    // Charts
    renderCategoryChart(data.category_analysis);
    renderBucketChart(data.bucket_totals, data.bucket_pcts);

    // Category table
    renderCategoryTable(data.category_analysis);

    // Recommendations
    renderRecommendations(data.recommendations, "recommendations-list");

    // Goal recommendations
    const goalSection = document.getElementById("goal-recs-section");
    if (data.goal_recommendations && data.goal_recommendations.length > 0) {
        goalSection.hidden = false;
        renderRecommendations(data.goal_recommendations, "goal-recommendations-list");
    } else {
        goalSection.hidden = true;
    }

    // Flagged purchases
    renderFlagged(data.flagged_purchases);
}

/* ===== Charts ===== */

function renderCategoryChart(categoryAnalysis) {
    const ctx = document.getElementById("category-chart").getContext("2d");

    if (categoryChart) categoryChart.destroy();

    const labels = categoryAnalysis.map(c => c.category);
    const amounts = categoryAnalysis.map(c => c.amount);
    const colors = labels.map(l => CATEGORY_COLORS[l] || "#b2bec3");

    categoryChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: amounts,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: "#fff",
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "right",
                    labels: { font: { size: 11 }, padding: 8 },
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const val = ctx.parsed;
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((val / total) * 100).toFixed(1);
                            return ` $${val.toFixed(2)} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderBucketChart(bucketTotals, bucketPcts) {
    const ctx = document.getElementById("bucket-chart").getContext("2d");

    if (bucketChart) bucketChart.destroy();

    const labels = Object.keys(bucketTotals);
    const amounts = Object.values(bucketTotals);
    const targetPcts = [50, 30, 20];
    const colors = ["#0984e3", "#6c5ce7", "#00b894"];

    bucketChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Actual %",
                    data: labels.map(l => bucketPcts[l]),
                    backgroundColor: colors.map(c => c + "cc"),
                    borderColor: colors,
                    borderWidth: 2,
                },
                {
                    label: "Target %",
                    data: targetPcts,
                    backgroundColor: colors.map(c => c + "33"),
                    borderColor: colors,
                    borderWidth: 2,
                    borderDash: [5, 5],
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "% of Income" },
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: (ctx) => {
                            if (ctx.datasetIndex === 0) {
                                return `$${amounts[ctx.dataIndex].toFixed(2)}`;
                            }
                            return "";
                        }
                    }
                }
            }
        }
    });
}

/* ===== Category Table ===== */

function renderCategoryTable(categories) {
    const tbody = document.querySelector("#category-table tbody");
    tbody.innerHTML = "";

    categories.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${CATEGORY_COLORS[c.category] || '#b2bec3'};margin-right:6px;vertical-align:middle;"></span>${c.category}</td>
            <td class="amount">$${c.amount.toFixed(2)}</td>
            <td>${c.pct_of_income}%</td>
            <td>${c.guideline_pct}%</td>
            <td><span class="status-badge ${c.status}">${c.status === "ok" ? "On Track" : "Over"}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

/* ===== Recommendations ===== */

function renderRecommendations(recs, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";

    recs.forEach(r => {
        const div = document.createElement("div");
        div.className = `rec-card ${r.type}`;
        div.innerHTML = `
            <span class="rec-icon">${REC_ICONS[r.type] || ""}</span>
            <div class="rec-body">
                <strong>${escapeHtml(r.title)}</strong>
                <span>${escapeHtml(r.detail)}</span>
            </div>
        `;
        container.appendChild(div);
    });
}

/* ===== Flagged Purchases ===== */

function renderFlagged(flagged) {
    const section = document.getElementById("flagged-section");
    if (!flagged || flagged.length === 0) {
        section.hidden = true;
        return;
    }

    section.hidden = false;
    const tbody = section.querySelector("tbody");
    tbody.innerHTML = "";

    flagged.forEach(t => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${t.date}</td>
            <td><span class="flag-icon">[!]</span> ${escapeHtml(t.description)}</td>
            <td class="amount">$${t.amount.toFixed(2)}</td>
            <td>${t.category}</td>
        `;
        tbody.appendChild(tr);
    });
}

/* ===== Utilities ===== */

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
