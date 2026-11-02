/**
 * Dynamic Order Form Item Manager
 */

document.addEventListener('DOMContentLoaded', () => {
    initOrderForm();
});

function initOrderForm() {
    const addBtn = document.getElementById('btn-add-item-row');
    const itemsTableBody = document.getElementById('order-items-table-body');
    const orderForm = document.getElementById('order-creation-form');

    if (!itemsTableBody) return;

    if (addBtn) {
        addBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addItemRow();
        });
    }

    // Attach row events for initial row
    attachRowEventListeners(itemsTableBody);
    recalculateOrderTotals();

    if (orderForm) {
        orderForm.addEventListener('submit', (e) => {
            const rows = itemsTableBody.querySelectorAll('.order-item-row');
            if (rows.length === 0) {
                alert("Please add at least one product to the order.");
                e.preventDefault();
                return;
            }

            let valid = true;
            rows.forEach(row => {
                const select = row.querySelector('.product-select');
                const qtyInput = row.querySelector('.item-qty-input');
                const stock = parseInt(select.selectedOptions[0]?.getAttribute('data-stock') || '0', 10);
                const qty = parseInt(qtyInput.value, 10);

                if (!select.value) {
                    alert("Please select a product for all rows.");
                    valid = false;
                } else if (qty <= 0 || isNaN(qty)) {
                    alert("Quantity must be 1 or greater.");
                    valid = false;
                } else if (qty > stock) {
                    alert(`Selected quantity (${qty}) exceeds available stock (${stock}) for ${select.selectedOptions[0].text}.`);
                    valid = false;
                }
            });

            if (!valid) {
                e.preventDefault();
            }
        });
    }
}

function addItemRow() {
    const tbody = document.getElementById('order-items-table-body');
    const templateRow = tbody.querySelector('.order-item-row');
    if (!templateRow) return;

    const newRow = templateRow.cloneNode(true);
    // Reset values in cloned row
    const select = newRow.querySelector('.product-select');
    const qtyInput = newRow.querySelector('.item-qty-input');
    const priceDisplay = newRow.querySelector('.item-price-display');
    const subtotalDisplay = newRow.querySelector('.item-subtotal-display');
    const stockBadge = newRow.querySelector('.item-stock-badge');

    select.selectedIndex = 0;
    qtyInput.value = 1;
    priceDisplay.innerText = '$0.00';
    subtotalDisplay.innerText = '$0.00';
    stockBadge.innerText = 'Select product';
    stockBadge.className = 'badge badge-neutral item-stock-badge';

    tbody.appendChild(newRow);
    attachRowEventListeners(tbody);
    recalculateOrderTotals();
}

function attachRowEventListeners(tbody) {
    const rows = tbody.querySelectorAll('.order-item-row');
    rows.forEach(row => {
        const select = row.querySelector('.product-select');
        const qtyInput = row.querySelector('.item-qty-input');
        const removeBtn = row.querySelector('.btn-remove-row');

        // Prevent duplicate listener attachments by clearing clone replacement or one-time handler
        select.onchange = () => handleProductChange(row);
        qtyInput.oninput = () => handleQtyChange(row);
        if (removeBtn) {
            removeBtn.onclick = (e) => {
                e.preventDefault();
                const totalRows = tbody.querySelectorAll('.order-item-row').length;
                if (totalRows > 1) {
                    row.remove();
                    recalculateOrderTotals();
                } else {
                    alert("An order must contain at least one item.");
                }
            };
        }
    });
}

function handleProductChange(row) {
    const select = row.querySelector('.product-select');
    const qtyInput = row.querySelector('.item-qty-input');
    const priceDisplay = row.querySelector('.item-price-display');
    const stockBadge = row.querySelector('.item-stock-badge');

    const opt = select.selectedOptions[0];
    if (!opt || !opt.value) {
        priceDisplay.innerText = '$0.00';
        stockBadge.innerText = 'Select product';
        stockBadge.className = 'badge badge-neutral item-stock-badge';
        recalculateRowSubtotal(row);
        return;
    }

    const price = parseFloat(opt.getAttribute('data-price') || '0');
    const stock = parseInt(opt.getAttribute('data-stock') || '0', 10);

    priceDisplay.innerText = '$' + price.toFixed(2);
    qtyInput.max = stock;

    if (stock <= 0) {
        stockBadge.innerText = 'Out of Stock (0)';
        stockBadge.className = 'badge badge-danger item-stock-badge';
    } else if (stock <= 5) {
        stockBadge.innerText = `Low Stock (${stock})`;
        stockBadge.className = 'badge badge-warning item-stock-badge';
    } else {
        stockBadge.innerText = `In Stock (${stock})`;
        stockBadge.className = 'badge badge-success item-stock-badge';
    }

    recalculateRowSubtotal(row);
}

function handleQtyChange(row) {
    const select = row.querySelector('.product-select');
    const qtyInput = row.querySelector('.item-qty-input');
    const stock = parseInt(select.selectedOptions[0]?.getAttribute('data-stock') || '0', 10);
    let qty = parseInt(qtyInput.value, 10);

    if (isNaN(qty) || qty < 1) {
        qty = 1;
        qtyInput.value = 1;
    }
    if (stock > 0 && qty > stock) {
        qtyInput.value = stock;
    }

    recalculateRowSubtotal(row);
}

function recalculateRowSubtotal(row) {
    const select = row.querySelector('.product-select');
    const qtyInput = row.querySelector('.item-qty-input');
    const subtotalDisplay = row.querySelector('.item-subtotal-display');

    const price = parseFloat(select.selectedOptions[0]?.getAttribute('data-price') || '0');
    const qty = parseInt(qtyInput.value || '1', 10);
    const subtotal = price * qty;

    subtotalDisplay.innerText = '$' + subtotal.toFixed(2);
    recalculateOrderTotals();
}

function recalculateOrderTotals() {
    const tbody = document.getElementById('order-items-table-body');
    if (!tbody) return;

    let grandTotal = 0;
    const rows = tbody.querySelectorAll('.order-item-row');
    rows.forEach(row => {
        const select = row.querySelector('.product-select');
        const qtyInput = row.querySelector('.item-qty-input');
        const price = parseFloat(select.selectedOptions[0]?.getAttribute('data-price') || '0');
        const qty = parseInt(qtyInput.value || '0', 10);
        grandTotal += (price * qty);
    });

    const grandTotalEl = document.getElementById('order-grand-total');
    if (grandTotalEl) {
        grandTotalEl.innerText = '$' + grandTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
}
