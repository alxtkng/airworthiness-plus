/* Data tables: one line for each row, opened on click (design-system/Components.md).

   Without this script every table shows every cell in full. With it, a row is one
   line and a button opens a detail row beneath it holding every column's full value.
   A column that holds a form is shown only in the detail, and its form is moved
   there, not copied, so there is one of each control on the page. */
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
    table.classList.add("compact");
  }

  document.documentElement.classList.add("js");
  Array.prototype.forEach.call(
    document.querySelectorAll("main table:not([data-plain])"),
    enhance
  );
})();
