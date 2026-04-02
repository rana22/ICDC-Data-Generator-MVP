// function initGrid() {
//   const root = document.querySelector("#table-root");
//   if (!root || root.dataset.agReady === "true") return;
//   if (typeof agGrid === "undefined") return;

//   const rowTag = document.querySelector("#table-root-data");
//   const colTag = document.querySelector("#table-root-cols");
//   if (!rowTag || !colTag) return;

//   let rowData = [];
//   let colDefs = [];

//   try {
//     rowData = JSON.parse(rowTag.textContent || "[]");
//     colDefs = JSON.parse(colTag.textContent || "[]");
//   } catch (e) {
//     console.error("JSON parse error:", e);
//     console.log("Row raw:", rowTag.textContent);
//     console.log("Col raw:", colTag.textContent);
//     return;
//   }

//   const INDEX_FIELDS = ["index", "level_0"];

//   rowData = rowData.map(row => {
//     const cleaned = { ...row };
//     INDEX_FIELDS.forEach(f => delete cleaned[f]);
//     return cleaned;
//   });

//   // Enhance column defs (auto-wrap long text)
//   colDefs = colDefs.filter(col => !INDEX_FIELDS.includes(col.field))
//   .map(col => ({
//     ...col,
//     wrapText: true,
//     autoHeight: true,
//   }));

//   const gridOptions = {
//     columnDefs: colDefs,
//     rowData: rowData,

//     defaultColDef: {
//       sortable: true,
//       filter: true,
//       resizable: true,
//       minWidth: 120
//       // ❌ removed flex to allow autosize to work properly
//     },

//     pagination: true,
//     paginationPageSize: 25,

//     onGridReady: (params) => {
//       // Auto-size columns to content
//       const allCols = params.columnApi.getColumns().map(c => c.getId());
//       params.columnApi.autoSizeColumns(allCols);

//       // Optional: limit max width (prevents crazy wide columns)
//       allCols.forEach(colId => {
//         const col = params.columnApi.getColumn(colId);
//         const width = col.getActualWidth();
//         if (width > 400) {
//           params.columnApi.setColumnWidth(colId, 400);
//         }
//       });
//     }
//   };

//   agGrid.createGrid(root, gridOptions);

//   root.dataset.agReady = "true";
// }

// window.addEventListener("load", initGrid);
// new MutationObserver(initGrid).observe(document.body, { childList: true, subtree: true });

function expandableTextRenderer(params) {
  const maxLen = 80;
  const fullText = params.value == null ? "" : String(params.value);
  const isLong = fullText.length > maxLen;

  let expanded = false;

  const eGui = document.createElement("div");
  eGui.style.whiteSpace = "normal";
  eGui.style.lineHeight = "1.3";

  const textSpan = document.createElement("span");
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.style.marginLeft = "6px";
  toggle.style.border = "none";
  toggle.style.background = "none";
  toggle.style.padding = "0";
  toggle.style.cursor = "pointer";
  toggle.style.color = "#0b5fff";
  toggle.style.fontSize = "12px";

  function render() {
    textSpan.textContent =
      !isLong || expanded ? fullText : fullText.slice(0, maxLen) + "...";

    toggle.textContent = expanded ? "show less" : "show more";
    toggle.style.display = isLong ? "inline" : "none";
  }

  toggle.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    expanded = !expanded;
    render();

    if (params.api) {
      params.api.resetRowHeights();
    }
  });

  eGui.appendChild(textSpan);
  eGui.appendChild(toggle);
  render();

  return eGui;
}

let gridApi = null;

function initGrid() {
  const root = document.querySelector("#table-root");
  if (!root || root.dataset.agReady === "true") return;
  if (typeof agGrid === "undefined") return;

  const rowTag = document.querySelector("#table-root-data");
  const colTag = document.querySelector("#table-root-cols");
  const searchInput = document.querySelector("#table-search");

  if (!rowTag || !colTag) return;

  let rowData = [];
  let colDefs = [];

  try {
    rowData = JSON.parse(rowTag.textContent || "[]");
    colDefs = JSON.parse(colTag.textContent || "[]");
  } catch (e) {
    console.error("JSON parse error:", e);
    console.log("Row raw:", rowTag.textContent);
    console.log("Col raw:", colTag.textContent);
    return;
  }

  const INDEX_FIELDS = ["index", "level_0"];

  rowData = rowData.map(row => {
    const cleaned = { ...row };
    INDEX_FIELDS.forEach(f => delete cleaned[f]);
    return cleaned;
  });

  const LONG_TEXT_COLUMNS = ["evidence", "a_to_b_mapping", "classification"];

  colDefs = colDefs
  .filter(col => !INDEX_FIELDS.includes(col.field))
  .map(col => {
    const isLongText = LONG_TEXT_COLUMNS.includes(col.field);

    return {
      ...col,
      wrapText: true,
      autoHeight: true,
      cellRenderer: isLongText ? expandableTextRenderer : undefined,
    };
  });

  const gridOptions = {
    columnDefs: colDefs,
    rowData: rowData,

    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
      minWidth: 120,
    },

    pagination: true,
    paginationPageSize: 25,

    onGridReady: (params) => {
      gridApi = params.api;

      const allCols = params.columnApi.getColumns().map(c => c.getId());
      params.columnApi.autoSizeColumns(allCols);

      allCols.forEach(colId => {
        const col = params.columnApi.getColumn(colId);
        const width = col.getActualWidth();
        if (width > 400) {
          params.columnApi.setColumnWidth(colId, 400);
        }
      });
    }
  };

  agGrid.createGrid(root, gridOptions);

  // Hook up search box
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const value = e.target.value || "";
      if (gridApi) {
        gridApi.setGridOption("quickFilterText", value);
      }
    });
  }

  root.dataset.agReady = "true";
}

window.addEventListener("load", initGrid);
new MutationObserver(initGrid).observe(document.body, { childList: true, subtree: true });