STATUS_URL = "https://pmcstatusprimary.blob.core.windows.net/dynamic-public-data/repository_status.json"

/**
 * Get mirror status from STATUS_URL and generate HTML content for the page.
 */
function get_mirror() {
  $.getJSON(STATUS_URL, function (status) {
    if (!("mirror" in status)) {
      document.getElementById("main-content").innerHTML = "No status";
      return;
    }
    mirror_status = status.mirror

    table_body_content = ''

    $.each(mirror_status, function (mirror, status) {
      if ("running" in status && status["running"] == true) {
        mirror_color = "green"
        svg = '<img src = "svg-check.svg" width="18px" height="18px" alt="Running"/>'
      } else {
        mirror_color = "red"
        svg = '<img src = "svg-error.svg" width="18px" height="18px" alt="Fail"/>'
      }

      if ("time" in status) {
        time_str = get_elapsed_time_string(status["time"])
      } else {
        time_str = ""
      }

      table_body_content += `
        <tr>
          <td class="text-center">${svg}</td>
          <td scope="row">${mirror}</td>
          <td scope="row">${time_str}</td>
        </tr>`
    });
    page = `
      <table class="table table-striped w-auto table-bordered">
        <thead>
          <tr>
            <th scope="col">Status</th>
            <th scope="col">Mirror Url</th>
            <th scope="col">Last Checked</th>
          </tr>
        </thead>
        <tbody>
          ${table_body_content}
        </tbody>
      </table>`

    /* Add HTML content to the page. */
    document.getElementById("main-content").innerHTML = page
  });
}

/**
 * Returns true if the checkbox is checked, false otherwise.
 * 
 * @param {string} checkbox_id Id of checkbox element
 * @returns boolean
 */
function is_checked(checkbox_id) {
  elem = document.getElementById(checkbox_id)
  return elem == null || elem.checked
}

/**
 * Get an elapsed time string. The update time is expected
 * to be formatted as a UTC string.
 * 
 * @param {string} update_time_str 
 * @returns Elapsed time as a readable string.
 */
function get_elapsed_time_string(update_time_str) {
  _MS_PER_SECOND = 1000
  _MS_PER_MINUTE = _MS_PER_SECOND * 60
  _MS_PER_HOUR = _MS_PER_MINUTE * 60
  _MS_PER_DAY = _MS_PER_HOUR * 24

  update_time_str = update_time_str.substring(0, update_time_str.length - 7)
  update_time_str = update_time_str.replace(/-/g, '/')
  const time_now = new Date()
  const update_time = new Date(update_time_str + " UTC")

  milli_diff = time_now - update_time

  day_diff = Math.floor(milli_diff / _MS_PER_DAY)
  hour_diff = Math.floor(milli_diff / _MS_PER_HOUR)
  minute_diff = Math.floor(milli_diff / _MS_PER_MINUTE)
  second_diff = Math.floor(milli_diff / _MS_PER_SECOND)

  if (day_diff > 0) {
    return `${day_diff} day${day_diff == 1 ? "" : "s"} ago`
  } else if (hour_diff > 0) {
    return `${hour_diff} hour${hour_diff == 1 ? "" : "s"} ago`
  } else if (minute_diff > 0) {
    return `${minute_diff} minute${minute_diff == 1 ? "" : "s"} ago`
  } else {
    return `${second_diff} second${second_diff == 1 ? "" : "s"} ago`
  }
}

/**
 * Get repository status from STATUS_URL and generate HTML content for the page.
 * 
 * @param {string} type Either "apt" or "yum".
 */
function get_repo(type) {
  $.getJSON(STATUS_URL, function (status) {
    inc_running = is_checked("good-checkbox")
    inc_critical = is_checked("error-checkbox")
    inc_empty = is_checked("empty-checkbox")
    idx = 0;
    if (!(type in status)) {
      document.getElementById("main-content").innerHTML = "No status";
      return;
    }
    apt_status = status[type];

    accordion_content = ``
    $.each(apt_status, function (repo, repo_data) {
      empty = false
      if (repo_data["state"] == "empty") {
        if (!inc_empty) {
          return;
        }
        style = "custom-accordion-empty"
        svg = '<img src = "svg-empty.svg" width="18px" height="18px" alt="Empty"/>'
        empty = true
      } else if (repo_data["state"] == "ok") {
        if (!inc_running) {
          return;
        }
        style = "custom-accordion-success"
        svg = '<img src = "svg-check.svg" width="18px" height="18px" alt="Running"/>'
      } else {
        if (!inc_critical) {
          return;
        }
        style = "custom-accordion-fail" // default to error
        svg = '<img src = "svg-error.svg" width="18px" height="18px" alt="Fail"/>'
      }

      if ("time" in repo_data) {
        time_str = get_elapsed_time_string(repo_data["time"])
      } else {
        time_str = ""
      }
      last_updated = `<span style="color: grey">Checked ${time_str}</span>`

      accordion_body_content = ``
      if (empty) {
        accordion_body_content += "This repository is empty"
      } else {
        $.each(repo_data["dists"], function (dist, dist_data) {
          if (dist_data["state"] == "ok") {
            error_str = "No errors"
            dist_color = "green"
            error_desc = ""
          } else {
            err_count = dist_data["dist_errors"].length
            if (err_count == 1) {
              error_str = "1 error found: "
            } else {
              error_str = `${err_count} errors found:`
            }
            dist_color = "red"
            error_desc = "<ul>"
            for (var error of dist_data["dist_errors"]) {
              error_desc += `<li>${error}</li>`
            }
            error_desc += "</ul>"
          }

          if (dist == "yum_dist" || dist == "apt_dist") {
            title = `${error_str}`
          } else {
            title = `>> ${dist}: ${error_str}`
          }
          dist_errors_button = ``
          dist_errors_content = ``

          if (error_desc.length > 0) {
            dist_errors_button = `
              <button class="btn btn-secondary btn-sm" type="button"
                data-bs-toggle="collapse" 
                data-bs-target="#errors-div${idx}" aria-expanded="false" 
                aria-controls="errors-div${idx}">
                Errors
              </button>`
            dist_errors_content = `
              <div class="collapse" id="errors-div${idx}">
                <div class="card card-body">
                  ${error_desc}
                </div>
              </div>`
            idx += 1
          }
          accordion_body_content += `
          <p style="color:${dist_color}">
            ${title} ${dist_errors_button}
          </p>
          ${dist_errors_content}`
        });
      }
      button_text = `
        <div class="container">
          <div class="row">
            <div class="col-md-auto">${svg}</div>
            <div class="col">${repo}</div>
            <div class="col-md-auto">${last_updated}</div>
          </div>
        </div>`
      accordion_content += `
        <div class="accordion-item ${style}">
          <h2 class="accordion-header" id="panelHeading${idx}">
            <button class="accordion-button collapsed" type="button" 
            data-bs-toggle="collapse" data-bs-target="#panelCollapse${idx}" 
            aria-expanded="true" aria-controls="panelCollapse${idx}">
              ${button_text}
            </button>
          </h2>
          <div id="panelCollapse${idx}" class="accordion-collapse collapse"
            aria-labelledby="panelHeading${idx}">
            <div class="accordion-body">
              ${accordion_body_content}
            </div>
          </div>
        </div>`

      idx++
    });
    page = `
      <div class="accordion">
        ${accordion_content}
      </div>`

    /* Add HTML content to the page. */
    document.getElementById("main-content").innerHTML = page
  });
}

/**
 * Wrapper for get_mirror and get_repo. Useful for the reload button.
 * 
 * @param {string} type Either "mirror", "apt", "yum".
 */
function load_refresh(type) {
  if (type == "mirror") {
    get_mirror()
  } else if (type == "apt") {
    get_repo("apt")
  } else if (type == "yum") {
    get_repo("yum")
  }
}
