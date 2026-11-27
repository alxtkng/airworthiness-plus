/* Data tables: one line for each row, opened on click (design-system/Components.md).

   Without this script every table shows every cell in full. With it, a row is one
   line and a button opens a detail row beneath it holding every column's full value.
   A column that holds a form is shown only in the detail, and its form is moved
   there, not copied, so there is one of each control on the page.

   A column heading is a button that sorts by that column: once ascending, again
   descending. Dates sort as dates, numbers as numbers, a Status column by how
   serious it is with red first, and anything else as text. An empty cell comes
   last either way. A row keeps the rows beneath it that belong to it.

   A table of more than 10 rows, or one that asks for it with data-search="always"
   as the Fleet does, has a search above it and, beneath it, how many of its rows
   are shown. A row is shown when it holds every word typed, in any
   column, whatever the case. */
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
  /* The application writes a negative number with a minus sign, not a hyphen. */
  var NUMBER = /^[-\u2212]?\d[\d,]*(\.\d+)?/;
  var SEVERITY = ["status-stop", "status-due", "status-ok"];
  /* Within one colour, the worse word first, as the Fleet orders them. */
  var WORDS = ["overdue", "unserviceable", "within tolerance", "due", "due soon", "to assess"];

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
    return found ? Number(found[0].replace(/,/g, "").replace("\u2212", "-")) : null;
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

  function wordOf(text) {
    var found = WORDS.indexOf(text.toLowerCase());
    return found === -1 ? WORDS.length : found;
  }

  /* How a column sorts. A key is where the cell stands among kinds of cell, its
     value, and its text; an empty cell has no key and comes last. A column of
     dates or numbers is read as such when most of its cells are; a cell that is
     not one comes after those that are. A Status column runs from a row marked
     as needing attention, through red, amber and green, to no mark. */
  function keysOf(cells) {
    var texts = cells.map(textOf);
    var filled = texts.filter(function (text) {
      return text;
    });
    if (
      cells.some(function (cell) {
        return cell.querySelector(".status") || cell.hasAttribute("data-attention");
      })
    ) {
      return cells.map(function (cell, index) {
        if (cell.hasAttribute("data-attention")) {
          return [-1, 0, texts[index].toLowerCase()];
        }
        if (!texts[index]) {
          return null;
        }
        return [severityOf(cell), wordOf(texts[index]), texts[index].toLowerCase()];
      });
    }
    function mostly(read) {
      var read_ = filled.filter(function (text) {
        return read(text) !== null;
      });
      return filled.length > 0 && read_.length * 2 > filled.length;
    }
    var read = mostly(dateOf) ? dateOf : mostly(numberOf) ? numberOf : null;
    return texts.map(function (text) {
      if (!text) {
        return null;
      }
      var value = read ? read(text) : null;
      // The last part says the cell is not of the column's kind and stays after those that are.
      return value === null
        ? [0, 0, text.toLowerCase(), read !== null]
        : [0, value, text.toLowerCase(), false];
    });
  }

  function compare(a, b) {
    if (a[1] !== b[1]) {
      return a[1] < b[1] ? -1 : 1;
    }
    return a[2].localeCompare(b[2], "en-GB", { numeric: true });
  }

  /* Each row of a body with the rows that follow it and belong to it. */
  function groupsOf(body, rows) {
    var groups = [];
    Array.prototype.forEach.call(body.rows, function (row) {
      if (rows.indexOf(row) !== -1 || !groups.length) {
        groups.push([row]);
      } else {
        groups[groups.length - 1].push(row);
      }
    });
    return groups;
  }

  var SEARCH_ABOVE = 10;
  var searches = 0;

  /* A search above a long table, and a count of the rows shown beneath it. */
  function searchable(table, rows) {
    if (rows.length <= SEARCH_ABOVE && table.getAttribute("data-search") !== "always") {
      return;
    }
    searches += 1;
    var box = document.createElement("p");
    box.className = "table-search";
    var label = document.createElement("label");
    label.className = "visually-hidden";
    label.htmlFor = "table-search-" + searches;
    label.textContent = "Search This Table";
    var input = document.createElement("input");
    input.type = "search";
    input.id = label.htmlFor;
    input.placeholder = "Search";
    input.autocomplete = "off";
    box.appendChild(label);
    box.appendChild(input);
    table.parentNode.insertBefore(box, table);
    var count = document.createElement("p");
    count.className = "table-count";
    count.setAttribute("role", "status");
    table.parentNode.insertBefore(count, table.nextSibling);

    function apply() {
      var words = input.value.toLowerCase().split(/\s+/).filter(function (word) {
        return word;
      });
      var shown = 0;
      Array.prototype.forEach.call(table.tBodies, function (body) {
        groupsOf(body, rows).forEach(function (group) {
          if (rows.indexOf(group[0]) === -1) {
            return;
          }
          // What the row holds, not what its forms offer: a list of choices or
          // the label on a button would match in every row.
          var text = group
            .map(function (row) {
              var copy = row.cloneNode(true);
              Array.prototype.forEach.call(copy.querySelectorAll(CONTROLS + ", label"), function (control) {
                control.parentNode.removeChild(control);
              });
              return copy.textContent;
            })
            .join(" ")
            .toLowerCase();
          var holds = words.every(function (word) {
            return text.indexOf(word) !== -1;
          });
          group.forEach(function (row) {
            row.classList.toggle("filtered", !holds);
          });
          shown += holds ? 1 : 0;
        });
      });
      count.textContent = shown + " of " + rows.length + " Shown";
    }

    input.addEventListener("input", apply);
    apply();
  }

  /* Sort the rows of each body by one column, each row with the rows that follow it. */
  function sortBy(table, rows, index, descending) {
    Array.prototype.forEach.call(table.tBodies, function (body) {
      var groups = groupsOf(body, rows);
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
        // A cell that is not of the column's kind stays after those that are.
        if (Boolean(keys[a][3]) !== Boolean(keys[b][3])) {
          return keys[a][3] ? 1 : -1;
        }
        var result = keys[a][0] !== keys[b][0] ? keys[a][0] - keys[b][0] : compare(keys[a], keys[b]);
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
      if (row.hasAttribute("data-open-details")) {
        button.click();
      }
    });
    sortable(table, rows, head, held);
    searchable(table, rows);
    table.classList.add("compact");
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-print]"), function (control) {
    control.hidden = false;
    control.addEventListener("click", function () {
      var collapsed = document.querySelectorAll("main details:not([open])");
      collapsed.forEach(function (detail) { detail.open = true; });
      window.print();
      collapsed.forEach(function (detail) { detail.open = false; });
    });
  });

  document.documentElement.classList.add("js");
  Array.prototype.forEach.call(
    document.querySelectorAll("main table:not([data-plain])"),
    enhance
  );
})();
