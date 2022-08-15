STATUS_URL = "https://pmcstatus.blob.core.windows.net/dynamic-public-data/repository_status.json"


/**
 * Returns plural form of word if count is more than 1,
 * otherwise returns singular
 * 
 * @param {int} count 
 * @param {string} singular 
 * @param {string} plural 
 * @returns 
 */
function pluralize(count, singular, plural) {
  if (count == 1) {
      return singular
  } else {
      return plural
  }
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
    return `${day_diff} ${pluralize(day_diff, "day", "days")} ago`
  } else if (hour_diff > 0) {
    return `${hour_diff} ${pluralize(hour_diff, "hour", "hours")} ago`
  } else if (minute_diff > 0) {
    return `${minute_diff} ${pluralize(minute_diff, "minute", "minutes")} ago`
  } else {
    return `${second_diff} ${pluralize(second_diff, "second", "seconds")} ago`
  }
}


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

    accordion_content = ""
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

      last_updated = ""
      if ("time" in repo_data) {
        time_str = get_elapsed_time_string(repo_data["time"])
        last_updated = `<span style="color: grey">Checked ${time_str}</span>`
      }

      accordion_body_items = ""
      if (empty) {
        accordion_body_items += `
        <li class="list-group-item">
          This repository is empty
        </li>`
      } else {
        $.each(repo_data["dists"], function (dist, dist_data) {
          if (dist_data["state"] == "ok") {
            error_str = "No errors"
            dist_color = "green"
            error_desc = ""
          } else {
            err_count = dist_data["dist_errors"].length
            error_str = `${err_count} ${pluralize(err_count, "error", "errors")} found:`
            dist_color = "red"
            error_desc = "<ul>"
            for (var error of dist_data["dist_errors"]) {
              error_desc += `<li>${error}</li>`
            }
            error_desc += "</ul>"
          }

          dist_last_updated = ""
          if (dist == "yum_dist" || dist == "apt_dist") {
            title = `<span style="color:${dist_color}"> ${error_str} </span>`
          } else {
            title = `<b>${dist}:</b> <span style="color:${dist_color}"> ${error_str} </span>`
            if ("time" in dist_data) {
              time_str = get_elapsed_time_string(dist_data["time"])
              dist_last_updated = `<span style="color: grey"> - Checked ${time_str}</span>`
            }
          }
          dist_errors_button = ""
          dist_errors_content = ""

          if (error_desc.length > 0) {
            dist_errors_button = `
              <img type="button"
                id="dropdown${idx}"
                onClick="dropdown_click(event)"
                data-bs-toggle="collapse" 
                data-bs-target="#errors-div${idx}" aria-expanded="false" 
                aria-controls="errors-div${idx}" 
                src = "svg-down.svg" width="24px" height="24px" alt="Fail"/>
              `
            dist_errors_content = `
              <div class="collapse" id="errors-div${idx}">
                <p>
                  <div class="card card-body">
                    ${error_desc}
                  </div>
                </p>
              </div>`
            idx += 1
          }

          accordion_body_items += `
          <li class="list-group-item">
              ${title} ${dist_last_updated} ${dist_errors_button}

            ${dist_errors_content}
          </li>`
        });
      }

      accordion_body_content = `
        <ul class="list-group list-group-flush">
          ${accordion_body_items}
        </ul>`

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
 * onClick function for error dropdowns. Switches dropdown arrow between
 * up and down arrow. 
 * 
 * @param {PointerEvent} event 
 */
function dropdown_click(event) {
  console.log(event)
  if (event.target.src.includes("svg-down.svg")) {
    event.target.src = "svg-up.svg"
  } else {
    event.target.src = "svg-down.svg"
  }
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
