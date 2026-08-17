const detailContainer =
  document.getElementById(
    "node-detail"
  );


function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function safeUrl(url) {
  if (!url) {
    return null;
  }

  try {
    const parsed =
      new URL(url);

    if (
      parsed.protocol === "https:" ||
      parsed.protocol === "http:"
    ) {
      return parsed.href;
    }

  } catch {}

  return null;
}


function safeIconPath(path) {
  if (!path) {
    return null;
  }

  const value =
    String(path)
      .replaceAll("\\", "/")
      .replace(/^\.?\//, "");

  if (
    value.includes("..")
  ) {
    return null;
  }

  if (
    !value.startsWith(
      "assets/icons/"
    )
  ) {
    return null;
  }

  return value;
}


function createFallback(name) {
  const letter =
    (
      name
        ?.trim()
        ?.charAt(0)
      ||
      "N"
    ).toUpperCase();

  return `
    <div
      class="detail-icon fallback-icon"
    >
      ${escapeHtml(letter)}
    </div>
  `;
}


function createIcon(node) {
  const icon =
    safeIconPath(
      node.iconDark ||
      node.icon ||
      node.iconLight
    );

  if (!icon) {
    return createFallback(
      node.displayName ||
      node.name
    );
  }

  return `
    <div class="detail-icon">

      <img
        src="${escapeHtml(icon)}"
        alt=""
        onerror="
          this.style.display='none';
          this.parentElement.classList.add('fallback-icon');
          this.parentElement.textContent='${escapeHtml(
            (
              node.displayName ||
              node.name ||
              "N"
            )
              .charAt(0)
              .toUpperCase()
          )}';
        "
      >

    </div>
  `;
}


function formatMetric(value) {
  const number =
    Number(value);

  if (
    !Number.isFinite(number)
  ) {
    return "—";
  }

  if (
    number >= 0 &&
    number <= 1
  ) {
    return (
      Math.round(
        number * 100
      ) + "%"
    );
  }

  return number.toFixed(2);
}


function createCategories(node) {
  const categories =
    (
      node.categories || []
    )
      .filter(Boolean)
      .filter(
        item =>
          item !== "Official"
      );

  if (
    !categories.length
  ) {
    return `
      <span class="detail-muted">
        Uncategorized
      </span>
    `;
  }

  return categories
    .map(
      category => `
        <span class="category detail-category">
          ${escapeHtml(category)}
        </span>
      `
    )
    .join("");
}


function extractSubcategories(
  value
) {
  if (!value) {
    return [];
  }

  if (
    Array.isArray(value)
  ) {
    return value
      .filter(Boolean)
      .map(String);
  }

  if (
    typeof value === "object"
  ) {
    const result = [];

    Object.entries(value)
      .forEach(
        ([key, nested]) => {

          if (
            Array.isArray(nested)
          ) {
            nested.forEach(
              item => {
                if (item) {
                  result.push(
                    String(item)
                  );
                }
              }
            );

            return;
          }

          if (
            nested &&
            typeof nested ===
              "string"
          ) {
            result.push(nested);
            return;
          }

          if (
            key &&
            nested === true
          ) {
            result.push(key);
          }
        }
      );

    return [
      ...new Set(result)
    ];
  }

  return [];
}


function createSubcategories(node) {
  const values =
    extractSubcategories(
      node.subcategories
    );

  if (!values.length) {
    return "";
  }

  return `
    <section class="detail-section">

      <h3>
        Subcategories
      </h3>

      <div class="detail-tags">

        ${
          values
            .map(
              item => `
                <span class="detail-tag">
                  ${escapeHtml(item)}
                </span>
              `
            )
            .join("")
        }

      </div>

    </section>
  `;
}


function createLinks(node) {
  const links =
    node.links || {};

  const repository =
    safeUrl(
      links.repository
    );

  const homepage =
    safeUrl(
      links.homepage
    );

  let npm =
    safeUrl(
      links.npm
    );

  if (
    !npm &&
    node.source ===
      "community" &&
    node.package
  ) {
    npm =
      "https://www.npmjs.com/package/" +
      encodeURIComponent(
        node.package
      );
  }

  const buttons = [];

  if (repository) {
    buttons.push(`
      <a
        class="detail-button"
        href="${escapeHtml(repository)}"
        target="_blank"
        rel="noopener noreferrer"
      >
        GitHub
      </a>
    `);
  }

  if (npm) {
    buttons.push(`
      <a
        class="detail-button"
        href="${escapeHtml(npm)}"
        target="_blank"
        rel="noopener noreferrer"
      >
        npm
      </a>
    `);
  }

  if (homepage) {
    buttons.push(`
      <a
        class="detail-button"
        href="${escapeHtml(homepage)}"
        target="_blank"
        rel="noopener noreferrer"
      >
        Website
      </a>
    `);
  }

  if (!buttons.length) {
    return `
      <span class="detail-muted">
        No external links available.
      </span>
    `;
  }

  return buttons.join("");
}


function detailRow(
  label,
  value
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    value = "—";
  }

  return `
    <div class="detail-row">

      <span>
        ${escapeHtml(label)}
      </span>

      <strong>
        ${escapeHtml(value)}
      </strong>

    </div>
  `;
}


function renderNode(node) {
  const displayName =
    node.displayName ||
    node.name ||
    "Unknown Node";

  const deprecated =
    Boolean(
      node.deprecated
    );

  document.title =
    `${displayName} · n8n Atlas`;

  detailContainer.className =
    "detail-content";

  detailContainer.innerHTML = `

    <section class="detail-hero">

      ${createIcon(node)}

      <div class="detail-title">

        <div class="detail-badges">

          <span
            class="badge ${escapeHtml(
              node.source
            )}"
          >
            ${escapeHtml(
              node.source
            )}
          </span>

          <span
            class="type-badge ${escapeHtml(
              node.nodeKind ||
              "action"
            )}"
          >
            ${escapeHtml(
              node.nodeKind ||
              "action"
            )}
          </span>

          ${
            node.verified
              ? `
                <span class="verified-badge">
                  Verified
                </span>
              `
              : ""
          }

          ${
            deprecated
              ? `
                <span class="deprecated-badge">
                  Deprecated
                </span>
              `
              : `
                <span class="active-badge">
                  Active
                </span>
              `
          }

        </div>

        <h1>
          ${escapeHtml(displayName)}
        </h1>

        <p class="detail-package">
          ${escapeHtml(
            node.package || ""
          )}
        </p>

      </div>

    </section>


    ${
      deprecated
        ? `
          <div class="deprecated-warning">

            <strong>
              Deprecated
            </strong>

            <span>
              ${
                typeof node.deprecated ===
                  "string"
                  ? escapeHtml(
                      node.deprecated
                    )
                  : (
                    "This integration is marked as deprecated."
                  )
              }
            </span>

          </div>
        `
        : ""
    }


    <section class="detail-description">

      <p>
        ${escapeHtml(
          node.description ||
          "No description available."
        )}
      </p>

    </section>


    <section class="detail-section">

      <h3>
        Categories
      </h3>

      <div class="detail-tags">
        ${createCategories(node)}
      </div>

    </section>


    ${createSubcategories(node)}


    <div class="detail-layout">

      <section class="detail-panel">

        <h3>
          Integration
        </h3>

        ${detailRow(
          "Source",
          node.source
        )}

        ${detailRow(
          "Type",
          node.nodeKind
        )}

        ${detailRow(
          "Version",
          node.version
        )}

        ${detailRow(
          "Publisher",
          node.publisher
        )}

        ${detailRow(
          "License",
          node.license
        )}

        ${detailRow(
          "Verified",
          node.verified
            ? "Yes"
            : "No"
        )}

        ${detailRow(
          "Status",
          deprecated
            ? "Deprecated"
            : "Active"
        )}

      </section>


      <section class="detail-panel">

        <h3>
          npm metrics
        </h3>

        ${detailRow(
          "Popularity",
          formatMetric(
            node.npmPopularity
          )
        )}

        ${detailRow(
          "Quality",
          formatMetric(
            node.npmQuality
          )
        )}

        ${detailRow(
          "Maintenance",
          formatMetric(
            node.npmMaintenance
          )
        )}

        ${detailRow(
          "Overall score",
          formatMetric(
            node.npmScore
          )
        )}

      </section>

    </div>


    <section class="detail-panel detail-technical">

      <h3>
        Technical information
      </h3>

      ${detailRow(
        "Package",
        node.package
      )}

      ${detailRow(
        "Node path",
        node.nodePath
      )}

      ${detailRow(
        "Metadata",
        node.metadataStatus
      )}

      ${detailRow(
        "Node ID",
        node.id
      )}

    </section>


    <section class="detail-section">

      <h3>
        Links
      </h3>

      <div class="detail-links">
        ${createLinks(node)}
      </div>

    </section>

  `;
}


function renderError(
  title,
  message
) {
  detailContainer.className =
    "detail-error";

  detailContainer.innerHTML = `
    <h1>
      ${escapeHtml(title)}
    </h1>

    <p>
      ${escapeHtml(message)}
    </p>

    <a
      href="./index.html"
      class="detail-button"
    >
      Back to Atlas
    </a>
  `;
}


const params =
  new URLSearchParams(
    window.location.search
  );

const nodeId =
  params.get("id");


if (!nodeId) {
  renderError(
    "Missing integration",
    "No integration ID was provided."
  );

} else {

  fetch(
    "./data/catalog.json"
  )

    .then(response => {

      if (!response.ok) {
        throw new Error(
          "Unable to load catalog."
        );
      }

      return response.json();
    })

    .then(nodes => {

      const node =
        nodes.find(
          item =>
            item.id === nodeId
        );

      if (!node) {
        renderError(
          "Integration not found",
          "This integration does not exist in the current catalog."
        );

        return;
      }

      renderNode(node);
    })

    .catch(error => {

      console.error(error);

      renderError(
        "Unable to load integration",
        "The catalog could not be loaded."
      );
    });
}