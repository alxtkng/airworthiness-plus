/* Data tables: one line for each row, opened on click (design-system/Components.md).

   Without this script every table shows every cell in full. With it, a row is one
   line and a button opens a detail row beneath it holding every column's full value.
   A column that holds a form is shown only in the detail, and its form is moved
   there, not copied, so there is one of each control on the page.

   A column heading is a button that sorts by that column: once ascending, again
   descending. Dates sort as dates, numbers as numbers, a Status column by how
   serious it is with red first, and anything else as text. An empty cell comes
   last either way. A row keeps the rows beneath it that belong to it. */
(function () {
  "use strict";

  var SVG = "http://www.w3.org/2000/svg";
  var CONTROLS = "form, input, select, textarea, button";

  function chevron() {
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "16");
    svg.setAttribute("height", "16");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.75");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    var path = document.createElementNS(SVG, "path");
    path.setAttribute("d", "M9 6l6 6-6 6");
    svg.appendChild(path);
    return svg;
  }

  function detailRow(row, headers, columns) {
    var detail = document.createElement("tr");
    detail.className = "detail";
    detail.hidden = true;
    var cell = document.createElement("td");
    cell.colSpan = columns + 1;
    var list = document.createElement("dl");
    Array.prototype.forEach.call(row.cells, function (source, index) {
      if (index === 0 || !headers[index - 1]) {
        return;
      }
      var group = document.createElement("div");
      var term = document.createElement("dt");
      term.textContent = headers[index - 1];
      var value = document.createElement("dd");
      if (source.classList.contains("in-detail")) {
        while (source.firstChild) {
          value.appendChild(source.firstChild);
        }
      } else {
        Array.prototype.forEach.call(source.childNodes, function (node) {
          value.appendChild(node.cloneNode(true));
        });
      }
      if (!value.textContent.trim() && !value.querySelector(CONTROLS)) {
        return;
      }
      // How a figure was worked out is a list of its own: give it the full width.
      if (value.querySelector("details")) {
        group.className = "wide";
      }
      group.appendChild(term);
      group.appendChild(value);
      list.appendChild(group);
    });
    cell.appendChild(list);
    detail.appendChild(cell);
    return detail;
  }

  var MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  var DATE = new RegExp("^(\\d{1,2}) (" + MONTHS.join("|") + ") (\\d{4})");
  var NUMBER = /^-?\d[\d,]*(\.\d+)?/;
  var SEVERITY = ["status-stop", "status-due", "status-ok"];

  function textOf(cell) {
    return cell.textContent.replace(/\s+/g, " ").trim();
  }

  function dateOf(text) {
    var found = DATE.exec(text);
    if (!found) {
      return null;
    }
    return Number(found[3]) * 10000 + (MONTHS.indexOf(found[2]) + 1) * 100 + Number(found[1]);
  }

  function numberOf(text) {
    var found = NUMBER.exec(text);
    return found ? Number(found[0].replace(/,/g, "")) : null;
  }

  function severityOf(cell) {
    var mark = cell.querySelector(".status");
    if (!mark) {
      return SEVERITY.length;
    }
    var found = SEVERITY.length;
    SEVERITY.forEach(function (name, index) {
      if (mark.classList.contains(name)) {
        found = index;
      }
    });
    return found;
  }

  /* How a column sorts: by the kind of thing every cell with something in it holds. */
  function keysOf(cells) {
    var texts = cells.map(textOf);
    var filled = texts.filter(function (text) {
      return text;
    });
    if (
      cells.some(function (cell) {
        return cell.querySelector(".status");
      })
    ) {
      return cells.map(function (cell, index) {
        return texts[index] ? [severityOf(cell), texts[index].toLowerCase()] : null;
      });
    }
    var read = null;
    if (filled.length && filled.every(dateOf)) {
      read = dateOf;
    } else if (
      filled.length &&
      filled.every(function (text) {
        return numberOf(text) !== null;
      })
    ) {
      read = numberOf;
    }
    return texts.map(function (text) {
      if (!text) {
        return null;
      }
      return [read ? read(text) : 0, text.toLowerCase()];
    });
  }

  function compare(a, b) {
    if (a[0] !== b[0]) {
      return a[0] < b[0] ? -1 : 1;
    }
    return a[1].localeCompare(b[1], "en-GB", { numeric: true });
  }

  /* Sort the rows of each body by one column, each row with the rows that follow it. */
  function sortBy(table, rows, index, descending) {
    Array.prototype.forEach.call(table.tBodies, function (body) {
      var groups = [];
      Array.prototype.forEach.call(body.rows, function (row) {
        if (rows.indexOf(row) !== -1 || !groups.length) {
          groups.push([row]);
        } else {
          groups[groups.length - 1].push(row);
        }
      });
      var keys = keysOf(
        groups.map(function (group) {
          return group[0].cells[index] || group[0].cells[0];
        })
      );
      var order = groups.map(function (_, position) {
        return position;
      });
      order.sort(function (a, b) {
        if (keys[a] === null || keys[b] === null) {
          return keys[a] === keys[b] ? a - b : keys[a] === null ? 1 : -1;
        }
        var result = compare(keys[a], keys[b]);
        return (descending ? -result : result) || a - b;
      });
      order.forEach(function (position) {
        groups[position].forEach(function (row) {
          body.appendChild(row);
        });
      });
    });
  }

  function sortable(table, rows, head, held) {
    Array.prototype.forEach.call(head.cells, function (cell, index) {
      if (index === 0 || held[index - 1]) {
        return;
      }
      var button = document.createElement("button");
      button.type = "button";
      button.className = "sort";
      while (cell.firstChild) {
        button.appendChild(cell.firstChild);
      }
      cell.appendChild(button);
      button.addEventListener("click", function () {
        var descending = cell.getAttribute("aria-sort") === "ascending";
        Array.prototype.forEach.call(head.cells, function (other) {
          other.removeAttribute("aria-sort");
        });
        cell.setAttribute("aria-sort", descending ? "descending" : "ascending");
        sortBy(table, rows, index, descending);
      });
    });
  }

  function enhance(table) {
    var head = table.tHead && table.tHead.rows[0];
    if (!head) {
      return;
    }
    var headers = Array.prototype.map.call(head.cells, function (cell) {
      return cell.textContent.trim();
    });
    var rows = [];
    Array.prototype.forEach.call(table.tBodies, function (body) {
      Array.prototype.forEach.call(body.rows, function (row) {
        if (row.cells.length === headers.length) {
          rows.push(row);
        }
      });
    });
    if (!rows.length) {
      return;
    }
    // A column is shown only in the detail if its heading says so, or if it holds a form.
    var held = headers.map(function (_, index) {
      return (
        head.cells[index].hasAttribute("data-detail") ||
        rows.some(function (row) {
          return row.cells[index].querySelector(CONTROLS);
        })
      );
    });
    var first = document.createElement("th");
    first.scope = "col";
    var name = document.createElement("span");
    name.className = "visually-hidden";
    name.textContent = "Details";
    first.appendChild(name);
    head.insertBefore(first, head.firstChild);
    held.forEach(function (inDetail, index) {
      if (inDetail) {
        head.cells[index + 1].classList.add("in-detail");
      }
    });
    var shown = held.filter(function (inDetail) {
      return !inDetail;
    }).length;
    Array.prototype.forEach.call(table.tBodies, function (body) {
      Array.prototype.forEach.call(body.rows, function (row) {
        if (rows.indexOf(row) === -1) {
          // A row that spans the table, such as an explanation: keep it aligned.
          if (row.cells.length === 1) {
            row.cells[0].colSpan = shown + 1;
          } else {
            row.insertBefore(document.createElement("td"), row.firstChild);
          }
        }
      });
    });
    rows.forEach(function (row) {
      held.forEach(function (inDetail, index) {
        if (inDetail) {
          row.cells[index].classList.add("in-detail");
        }
      });
      var cell = document.createElement("td");
      cell.className = "disclosure";
      var button = document.createElement("button");
      button.type = "button";
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", "Show Details");
      button.appendChild(chevron());
      cell.appendChild(button);
      row.insertBefore(cell, row.firstChild);
      var detail = null;
      button.addEventListener("click", function () {
        if (!detail) {
          detail = detailRow(row, headers, shown);
          row.parentNode.insertBefore(detail, row.nextSibling);
        }
        var open = detail.hidden;
        detail.hidden = !open;
        row.classList.toggle("open", open);
        button.setAttribute("aria-expanded", open ? "true" : "false");
      });
    });
    sortable(table, rows, head, held);
    table.classList.add("compact");
  }

  document.documentElement.classList.add("js");
  Array.prototype.forEach.call(
    document.querySelectorAll("main table:not([data-plain])"),
    enhance
  );
})();
