/* ============================================================
   ScrapeFlow — app.js
   ============================================================ */

const API_BASE_URL = "";

/* ------------------------------------------------------------
   API helper
   ------------------------------------------------------------ */
const Api = {
  async request(path, options = {}) {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" },
      ...options,
    });

    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }

    if (!res.ok || (data && data.success === false)) {
      const message = (data && data.error) || `Request failed (${res.status})`;
      throw new Error(message);
    }

    
    return data;
  },

  get(path) {
    return this.request(path, { method: "GET" });
  },

  post(path, body) {
    return this.request(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body || {}),
    });
  },

  discoverCompany(companyName) {
      return this.post("/api/company/discover", {
        company: companyName
      });
  },

  getJobs(params = {}) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== "" && v != null)
    ).toString();
    return this.get(`/api/jobs${qs ? `?${qs}` : ""}`);
  },

  getJob(jobId) {
    return this.get(`/api/jobs/${jobId}`);
  },

  uploadResume(file) {
    const formData = new FormData();
    formData.append("resume", file);
    return this.post("/api/resume/upload", formData);
  },

  createMatch(jobId, resumeId) {
  return this.post(`/api/match/${jobId}`, {
    resume_id: resumeId
  });
},

  getMatch(matchId) {
    return this.get(`/api/match/${matchId}`);
  },
};

/* ------------------------------------------------------------
   Toasts
   ------------------------------------------------------------ */
const Toast = {
  stack: null,

  ensureStack() {
    if (!this.stack) {
      this.stack = document.createElement("div");
      this.stack.className = "toast-stack";
      document.body.appendChild(this.stack);
    }
    return this.stack;
  },

  show(message, type = "info", duration = 4200) {
    const stack = this.ensureStack();
    const icons = { success: "fa-circle-check", error: "fa-circle-exclamation", info: "fa-circle-info" };

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <i class="fa-solid ${icons[type] || icons.info} toast-icon"></i>
      <div class="toast-msg">${Utils.escapeHtml(message)}</div>
      <button class="toast-close" aria-label="Dismiss"><i class="fa-solid fa-xmark"></i></button>
    `;

    toast.querySelector(".toast-close").addEventListener("click", () => toast.remove());
    stack.appendChild(toast);

    setTimeout(() => toast.remove(), duration);
  },

  success(msg) { this.show(msg, "success"); },
  error(msg) { this.show(msg, "error"); },
  info(msg) { this.show(msg, "info"); },
};

/* ------------------------------------------------------------
   Small utils
   ------------------------------------------------------------ */
const Utils = {
  escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
  },

  formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  },

  debounce(fn, wait = 300) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  },

  qs(name) {
    return new URLSearchParams(window.location.search).get(name);
  },

  setButtonLoading(btn, loading) {
    if (!btn) return;
    btn.classList.toggle("is-loading", loading);
    btn.disabled = loading;
  },
};

/* ------------------------------------------------------------
   Homepage: company discovery
   ------------------------------------------------------------ */
function initHomepage() {
  const form = document.getElementById("discover-form");
  if (!form) return;

  const input = document.getElementById("company-input");
  const button = document.getElementById("discover-btn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const companyName = input.value.trim();
    if (!companyName) {
      Toast.error("Enter a company name to continue.");
      input.focus();
      return;
    }

    Utils.setButtonLoading(button, true);

    try {
      await Api.discoverCompany(companyName);
      await Api.getJobs();
      window.location.href = "/jobs";
    } catch (err) {
      Toast.error(err.message || "Couldn't find that company. Try again.");
      Utils.setButtonLoading(button, false);
    }
  });
}

/* ------------------------------------------------------------
   Jobs listing page
   ------------------------------------------------------------ */
function initJobsPage() {
  const listEl = document.getElementById("job-list");
  if (!listEl) return;

  const state = {
    page: 1,
    perPage: 10,
    search: "",
    company: "",
    location: "",
    experience: "",
    job_type: "",
    skill: "",
    posted_date: "",
    jobs: [],
  };

  const searchInput = document.getElementById("job-search");
  const filterEls = {
    company: document.getElementById("filter-company"),
    location: document.getElementById("filter-location"),
    experience: document.getElementById("filter-experience"),
    job_type: document.getElementById("filter-job-type"),
    skill: document.getElementById("filter-skill"),
    posted_date: document.getElementById("filter-posted-date"),
  };
  const clearBtn = document.getElementById("clear-filters-btn");
  const refreshBtn = document.getElementById("refresh-jobs-btn");
  const countEl = document.getElementById("result-count");
  const paginationEl = document.getElementById("pagination");
  const companySearch = document.getElementById("company-search");
  const discoverBtn = document.getElementById("discover-company-btn");

  async function discoverCompanyFromJobsPage() {

    if (!companySearch || !discoverBtn) return;

    const companyName = companySearch.value.trim();

    if (!companyName) {
      Toast.error("Enter a company name.");
      companySearch.focus();
      return;
    }

    Utils.setButtonLoading(discoverBtn, true);

    try {

      Toast.info(`Discovering ${companyName} jobs...`);

      await Api.discoverCompany(companyName);

      Toast.success(`${companyName} jobs discovered successfully.`);

      // Reload jobs from database
      state.company = companyName;
      state.page = 1;

      await loadJobs();

      // Try selecting company in dropdown
      if (filterEls.company) {

        const option = [...filterEls.company.options].find(
          option =>
            option.value.toLowerCase() ===
            companyName.toLowerCase()
        );

        if (option) {
          filterEls.company.value = option.value;
        }

      }

    } catch (err) {

      console.error("Company discovery failed:", err);

      Toast.error(
        err.message ||
        `Unable to discover ${companyName} jobs.`
      );

    } finally {

      Utils.setButtonLoading(
        discoverBtn,
        false
      );

    }
  }

  if (discoverBtn) {

    discoverBtn.addEventListener(
      "click",
      discoverCompanyFromJobsPage
    );

  }

  if (companySearch) {

    companySearch.addEventListener(
      "keydown",
      (event) => {

        if (event.key === "Enter") {
          discoverCompanyFromJobsPage();
        }

      }
    );

  }
  async function loadJobs() {
    listEl.innerHTML = renderSkeleton();

    try {
      const params = {
        search: state.search,
        company: state.company,
        location: state.location,
        experience: state.experience,
        job_type: state.job_type,
        skill: state.skill,
        posted_date: state.posted_date,
      };
      const data = await Api.getJobs(params);
      state.jobs = (data && data.jobs) ? data.jobs : [];
      renderJobs();
    } catch (err) {
      state.jobs = [];
      renderJobs();
      Toast.error(err.message || "Unable to load live jobs.");
    }
  }

  function renderSkeleton() {
    return Array.from({ length: 4 }).map(() => `<div class="skeleton-row"></div>`).join("");
  }

  function renderJobs() {
    const jobs = state.jobs;
    countEl.innerHTML = `<strong>${jobs.length}</strong> jobs found`;

    if (!jobs.length) {
      listEl.innerHTML = `
        <div class="state-block">
          <div class="state-icon"><i class="fa-solid fa-magnifying-glass"></i></div>
          <h3>No jobs match your filters</h3>
          <p>Try a different company, location, or clear your filters to see everything we've discovered.</p>
          <button class="btn btn-secondary" id="empty-clear-btn">Clear filters</button>
        </div>
      `;
      const emptyClear = document.getElementById("empty-clear-btn");
      if (emptyClear) emptyClear.addEventListener("click", clearFilters);
      paginationEl.innerHTML = "";
      return;
    }

    const start = (state.page - 1) * state.perPage;
    const pageJobs = jobs.slice(start, start + state.perPage);

    listEl.innerHTML = pageJobs.map((job) => `
      <div class="job-card">
        <div class="job-card-main">
          <div class="job-card-top">
            <span class="job-card-title">${Utils.escapeHtml(job.title)}</span>
          </div>
          <div class="job-card-company">${Utils.escapeHtml(job.company)}</div>
          <div class="job-card-meta">
            <span><i class="fa-solid fa-location-dot"></i> ${Utils.escapeHtml(job.location)}</span>
            <span><i class="fa-solid fa-briefcase"></i> ${Utils.escapeHtml(job.experience)}</span>
            <span><i class="fa-solid fa-clock"></i> ${Utils.escapeHtml(job.job_type)}</span>
            <span><i class="fa-regular fa-calendar"></i> ${Utils.escapeHtml(job.posted_date)}</span>
          </div>
          <div class="badge-row">
            ${(job.skills || []).slice(0, 5).map((s) => `<span class="badge">${Utils.escapeHtml(s)}</span>`).join("")}
          </div>
        </div>
        <div class="job-card-actions">
          <a href="/jobs/${job.id}" class="btn btn-secondary btn-sm">View Job</a>
        </div>
      </div>
    `).join("");

    renderPagination(jobs.length);
  }

  function renderPagination(total) {
    const pageCount = Math.max(1, Math.ceil(total / state.perPage));
    if (pageCount <= 1) { paginationEl.innerHTML = ""; return; }

    let html = `<button class="page-btn" data-page="${state.page - 1}" ${state.page === 1 ? "disabled" : ""}><i class="fa-solid fa-chevron-left"></i></button>`;
    for (let i = 1; i <= pageCount; i++) {
      html += `<button class="page-btn ${i === state.page ? "active" : ""}" data-page="${i}">${i}</button>`;
    }
    html += `<button class="page-btn" data-page="${state.page + 1}" ${state.page === pageCount ? "disabled" : ""}><i class="fa-solid fa-chevron-right"></i></button>`;
    paginationEl.innerHTML = html;

    paginationEl.querySelectorAll(".page-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = parseInt(btn.dataset.page, 10);
        if (!isNaN(p) && p >= 1 && p <= pageCount) {
          state.page = p;
          renderJobs();
          listEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  function clearFilters() {
    state.search = ""; state.company = ""; state.location = "";
    state.experience = ""; state.job_type = ""; state.skill = ""; state.posted_date = "";
    state.page = 1;
    searchInput.value = "";
    Object.values(filterEls).forEach((el) => { if (el) el.value = ""; });
    loadJobs();
  }

  searchInput.addEventListener("input", Utils.debounce(() => {
    state.search = searchInput.value.trim();
    state.page = 1;
    loadJobs();
  }, 350));

  Object.entries(filterEls).forEach(([key, el]) => {
    if (!el) return;
    el.addEventListener("change", () => {
      state[key] = el.value;
      state.page = 1;
      loadJobs();
    });
  });

  clearBtn.addEventListener("click", clearFilters);
  refreshBtn.addEventListener("click", () => {
    Utils.setButtonLoading(refreshBtn, true);
    loadJobs().finally(() => Utils.setButtonLoading(refreshBtn, false));
  });

  loadJobs();
}

function fallbackJobs() {
  return [
    { id: 1, title: "Backend Engineer — Python", company: "TCS", location: "Bengaluru, IN", experience: "2-4 yrs", job_type: "Full-time", posted_date: "2 days ago", skills: ["Python", "Django", "PostgreSQL", "AWS"] },
    { id: 2, title: "Frontend Developer", company: "Infosys", location: "Pune, IN", experience: "1-3 yrs", job_type: "Full-time", posted_date: "3 days ago", skills: ["JavaScript", "React", "CSS", "HTML"] },
    { id: 3, title: "Data Analyst", company: "Microsoft", location: "Hyderabad, IN", experience: "0-2 yrs", job_type: "Full-time", posted_date: "5 days ago", skills: ["SQL", "Power BI", "Excel", "Python"] },
    { id: 4, title: "DevOps Engineer", company: "Wipro", location: "Chennai, IN", experience: "3-6 yrs", job_type: "Full-time", posted_date: "1 week ago", skills: ["Docker", "Kubernetes", "AWS", "CI/CD"] },
    { id: 5, title: "Full Stack Developer", company: "Accenture", location: "Remote", experience: "2-5 yrs", job_type: "Contract", posted_date: "1 week ago", skills: ["Node.js", "React", "MongoDB"] },
    { id: 6, title: "QA Automation Engineer", company: "TCS", location: "Mumbai, IN", experience: "1-4 yrs", job_type: "Full-time", posted_date: "2 weeks ago", skills: ["Selenium", "Java", "TestNG"] },
  ];
}

/* ------------------------------------------------------------
   Job detail page
   ------------------------------------------------------------ */
function initJobDetailPage() {
  const root = document.getElementById("job-detail-root");
  if (!root) return;

  const jobId = root.dataset.jobId;
  loadJobDetail(jobId);
}
function renderJobDetail(job) {

  const title =
    job.title || "Untitled Job";

  const company =
    job.company || "Unknown Company";

  const location =
    job.location || "Not specified";

  const experience =
    job.experience || "Not specified";

  const jobType =
    job.job_type || "Not specified";

  const source =
    job.source || "Company Website";

  const description =
    job.description ||
    "No job description available.";

  const postedDate =
    job.posted_date
      ? new Date(job.posted_date).toLocaleDateString(
          "en-IN",
          {
            day: "numeric",
            month: "short",
            year: "numeric"
          }
        )
      : "Not specified";


  /* =========================
     TITLE
  ========================= */

  const breadcrumbTitle =
    document.getElementById("detail-job-title");

  if (breadcrumbTitle) {
    breadcrumbTitle.textContent = title;
  }


  const heading =
    document.getElementById(
      "detail-job-title-heading"
    );

  if (heading) {
    heading.textContent = title;
  }


  /* =========================
     COMPANY
  ========================= */

  const companyName =
    document.getElementById(
      "detail-company-name"
    );

  if (companyName) {
    companyName.textContent = company;
  }


  const companyInitial =
    document.getElementById(
      "detail-company-initial"
    );

  if (companyInitial) {
    companyInitial.textContent =
      company.charAt(0).toUpperCase();
  }


  /* =========================
     META
  ========================= */

  const metaLocation =
    document.getElementById(
      "detail-meta-location"
    );

  if (metaLocation) {
    metaLocation.textContent = location;
  }


  const metaExperience =
    document.getElementById(
      "detail-meta-experience"
    );

  if (metaExperience) {
    metaExperience.textContent = experience;
  }


  const metaType =
    document.getElementById(
      "detail-meta-type"
    );

  if (metaType) {
    metaType.textContent = jobType;
  }


  const metaPosted =
    document.getElementById(
      "detail-meta-posted"
    );

  if (metaPosted) {
    metaPosted.textContent = postedDate;
  }


  /* =========================
     DESCRIPTION
  ========================= */

  const descriptionEl =
    document.getElementById(
      "detail-description"
    );

  if (descriptionEl) {

    descriptionEl.textContent =
      description;

    descriptionEl.style.whiteSpace =
      "pre-line";

  }


  /* =========================
     SKILLS
  ========================= */

  const skillsEl =
    document.getElementById(
      "detail-skills"
    );

  if (skillsEl) {

    const skills =
      Array.isArray(job.skills)
        ? job.skills
        : [];

    if (skills.length) {

      skillsEl.innerHTML =
        skills
          .map(
            skill => `
              <span class="badge">
                ${Utils.escapeHtml(skill)}
              </span>
            `
          )
          .join("");

    } else {

      skillsEl.innerHTML = `
        <span class="badge">
          Skills not specified
        </span>
      `;

    }

  }


  /* =========================
     QUALIFICATIONS
  ========================= */

  const qualificationsEl =
    document.getElementById(
      "detail-qualifications"
    );

  if (qualificationsEl) {

    const qualifications = [];

    if (experience !== "Not specified") {
      qualifications.push(
        `Experience: ${experience}`
      );
    }

    if (jobType !== "Not specified") {
      qualifications.push(
        `Employment type: ${jobType}`
      );
    }

    if (skillsEl && job.skills?.length) {
      qualifications.push(
        `Required skills: ${job.skills.join(", ")}`
      );
    }

    if (qualifications.length) {

      qualificationsEl.innerHTML =
        qualifications
          .map(
            item => `
              <li>
                ${Utils.escapeHtml(item)}
              </li>
            `
          )
          .join("");

    } else {

      qualificationsEl.innerHTML = `
        <li>
          No additional qualifications specified.
        </li>
      `;

    }

  }


  /* =========================
     SIDEBAR
  ========================= */

  const sidebarLocation =
    document.getElementById(
      "sidebar-location"
    );

  if (sidebarLocation) {
    sidebarLocation.textContent = location;
  }


  const sidebarExperience =
    document.getElementById(
      "sidebar-experience"
    );

  if (sidebarExperience) {
    sidebarExperience.textContent = experience;
  }


  const sidebarEmployment =
    document.getElementById(
      "sidebar-employment"
    );

  if (sidebarEmployment) {
    sidebarEmployment.textContent = jobType;
  }


  const sidebarPosted =
    document.getElementById(
      "sidebar-posted"
    );

  if (sidebarPosted) {
    sidebarPosted.textContent = postedDate;
  }


  const sidebarSource =
    document.getElementById(
      "sidebar-source"
    );

  if (sidebarSource) {
    sidebarSource.textContent = source;
  }


  /* =========================
     ORIGINAL JOB
  ========================= */

  const originalBtn =
    document.getElementById(
      "view-original-btn"
    );

  if (originalBtn) {

    if (job.source_url) {

      originalBtn.href =
        job.source_url;

      originalBtn.style.display =
        "inline-flex";

    } else {

      originalBtn.removeAttribute("href");

      originalBtn.style.display =
        "none";

    }

  }


  /* =========================
     MATCH RESUME
  ========================= */

  const matchBtn =
    document.getElementById(
      "match-resume-btn"
    );

  if (matchBtn && job.id) {

    matchBtn.href =
      `/jobs/${job.id}/upload`;

  }

}  

async function loadJobDetail(jobId) {
  const root = document.getElementById("job-detail-root");

  try {
    const data = await Api.getJob(jobId);

    if (!data || !data.job) {
      throw new Error("Job not found");
    }

    renderJobDetail(data.job);

  } catch (err) {
    root.classList.add("is-loaded");
    Toast.error(err.message || "Job not found.");
  }
}

/* ------------------------------------------------------------
   Upload resume page
   ------------------------------------------------------------ */
function initUploadPage() {
  const dropzone = document.getElementById("dropzone");
  if (!dropzone) return;

  const jobId = dropzone.closest("[data-job-id]")?.dataset.jobId;
  const fileInput = document.getElementById("resume-file-input");
  const preview = document.getElementById("file-preview");
  const fileNameEl = document.getElementById("file-name");
  const fileSizeEl = document.getElementById("file-size");
  const removeBtn = document.getElementById("file-remove-btn");
  const analyzeBtn = document.getElementById("analyze-btn");
  const progressTrack = document.getElementById("upload-progress-track");
  const progressFill = document.getElementById("upload-progress-fill");
  const statusMsg = document.getElementById("upload-status-msg");

  const MAX_SIZE = 10 * 1024 * 1024;
  const ALLOWED_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
  let selectedFile = null;

  function openPicker() { fileInput.click(); }

  dropzone.addEventListener("click", openPicker);
  dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") openPicker(); });

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
  });

  function handleFile(file) {
    hideStatus();
    dropzone.classList.remove("has-error");

    const extOk = /\.(pdf|docx)$/i.test(file.name);
    if (!ALLOWED_TYPES.includes(file.type) && !extOk) {
      showStatus("Unsupported file type. Please upload a PDF or DOCX file.", "error");
      dropzone.classList.add("has-error");
      return;
    }
    if (file.size > MAX_SIZE) {
      showStatus("File is too large. Maximum size is 10 MB.", "error");
      dropzone.classList.add("has-error");
      return;
    }

    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = Utils.formatBytes(file.size);
    preview.classList.add("is-visible");
    analyzeBtn.disabled = false;
  }

  removeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = "";
    preview.classList.remove("is-visible");
    analyzeBtn.disabled = true;
    hideStatus();
    resetProgress();
  });

  function showStatus(msg, type) {
    statusMsg.textContent = msg;
    statusMsg.className = `upload-status-msg is-visible status-${type}`;
  }
  function hideStatus() {
    statusMsg.classList.remove("is-visible");
  }
  function resetProgress() {
    progressTrack.classList.remove("is-visible");
    progressFill.style.width = "0%";
  }
  function animateProgress(to) {
    progressTrack.classList.add("is-visible");
    requestAnimationFrame(() => { progressFill.style.width = `${to}%`; });
  }

  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) {
      showStatus("Choose a resume file before analyzing.", "error");
      return;
    }

    Utils.setButtonLoading(analyzeBtn, true);
    hideStatus();
    animateProgress(35);

    try {
      const uploadRes = await Api.uploadResume(selectedFile);

      animateProgress(70);

      const resumeId = uploadRes?.resume?.id;

      if (!resumeId) {
        throw new Error("Resume was uploaded but resume ID was not returned.");
      }

      const matchRes = await Api.createMatch(jobId, resumeId);
      animateProgress(100);

      showStatus("Resume analyzed successfully. Redirecting to your results…", "success");
      Toast.success("Resume matched against this job.");

      const matchId = (matchRes && (matchRes.id || matchRes.match_id));

      if (!matchId) {
        throw new Error("Match was created but match ID was not returned.");
      }
      setTimeout(() => { window.location.href = `/match/${matchId}`; }, 700);
    } catch (err) {
      resetProgress();
      showStatus(err.message || "Something went wrong while analyzing your resume.", "error");
      Toast.error(err.message || "Resume analysis failed.");
      Utils.setButtonLoading(analyzeBtn, false);
    }
  });
}

/* ------------------------------------------------------------
   Match result page
   ------------------------------------------------------------ */
function initMatchResultPage() {
  const root = document.getElementById("match-result-root");
  if (!root) return;

  const matchId = root.dataset.matchId;
  loadMatchResult(matchId);
}

async function loadMatchResult(matchId) {
  try {
    const data = await Api.getMatch(matchId);

    if (!data || !data.id) {
      throw new Error("Match result is empty.");
    }

    renderMatch(data);

  } catch (err) {
    Toast.error(err.message || "Unable to load match result.");
  }
}
function fallbackMatch() {
  return {
    job_title: "Backend Engineer — Python",
    company: "TCS",
    location: "Bengaluru, IN",
    score: 78,
    label: "Good Match",
    matching_skills: ["Python", "SQL", "FastAPI", "REST APIs", "Git"],
    missing_skills: ["Docker", "AWS"],
    experience: { required: "2-5 years", resume: "3 years", status: "Strong Match" },
    education: { required: "Bachelor's degree", resume: "B.Tech Computer Science", status: "Match" },
    breakdown: { skills: 85, experience: 80, education: 90, projects: 75 },
    recommendation: "Your background lines up well with this role. Consider highlighting containerization or cloud deployment experience to close the remaining skill gaps.",
  };
}

function renderMatch(match) {
  document.getElementById("match-job-title").textContent = match.job_title || "This role";
  document.getElementById("match-company").textContent = match.company || "";
  document.getElementById("match-location").textContent = match.location || "";
  document.getElementById("match-company-initial").textContent = (match.company || "?").charAt(0);

  document.getElementById("score-label").textContent = match.label || "Match";
  document.getElementById("score-summary").innerHTML = `<strong>${match.score}%</strong> of the key requirements in this role line up with your resume.`;

  animateScoreRing(match.score || 0);

  document.getElementById("matching-skills").innerHTML = (match.matching_skills || [])
    .map((s) => `<span class="badge badge-success"><i class="fa-solid fa-check"></i> ${Utils.escapeHtml(s)}</span>`).join("") || `<span class="badge">No direct matches found</span>`;

  const relatedPanel = document.getElementById("related-skills-panel");
  const relatedEl = document.getElementById("related-skills");
  if (relatedEl && relatedPanel) {
    const relatedList = match.related_skills || [];
    if (relatedList.length > 0) {
      relatedPanel.style.display = "block";
      relatedEl.innerHTML = relatedList
        .map((r) => {
          const req = Utils.escapeHtml(
            r.required === "sql"
              ? "SQL"
              : r.required === "devops"
              ? "DevOps"
              : r.required
              ? r.required.charAt(0).toUpperCase() + r.required.slice(1)
              : ""
          );
          const cand = (r.candidate || [])
            .map((c) =>
              Utils.escapeHtml(
                c === "sql"
                  ? "SQL"
                  : c === "aws"
                  ? "AWS"
                  : c === "gcp"
                  ? "GCP"
                  : c === "ci/cd"
                  ? "CI/CD"
                  : c
                  ? c.charAt(0).toUpperCase() + c.slice(1)
                  : ""
              )
            )
            .join(", ");
          return `<span class="badge badge-accent" style="font-size:0.82rem; padding:6px 12px;"><i class="fa-solid fa-link"></i> <strong>${req}</strong> — demonstrated via ${cand}</span>`;
        })
        .join("");
    } else {
      relatedPanel.style.display = "none";
      relatedEl.innerHTML = "";
    }
  }

  document.getElementById("missing-skills").innerHTML = (match.missing_skills || [])
    .map((s) => `<span class="badge badge-danger"><i class="fa-solid fa-xmark"></i> ${Utils.escapeHtml(s)}</span>`).join("") || `<span class="badge badge-success">No gaps found</span>`;

  const exp = match.experience || {};
  document.getElementById("exp-required").textContent = exp.required || "—";
  document.getElementById("exp-resume").textContent = exp.candidate || exp.resume || "—";
  document.getElementById("exp-status").textContent = exp.status || "—";

  const edu = match.education || {};
  document.getElementById("edu-required").textContent = edu.required || "—";
  document.getElementById("edu-resume").textContent = edu.candidate || edu.resume || "—";
  document.getElementById("edu-status").textContent = edu.status || "—";

  const breakdown = match.breakdown || {};
  animateBar("bar-skills", breakdown.skills || 0);
  animateBar("bar-experience", breakdown.experience || 0);
  animateBar("bar-education", breakdown.education || 0);
  animateBar("bar-projects", breakdown.projects || 0);

  document.getElementById("val-skills").textContent = `${breakdown.skills || 0}%`;
  document.getElementById("val-experience").textContent = `${breakdown.experience || 0}%`;
  document.getElementById("val-education").textContent = `${breakdown.education || 0}%`;
  document.getElementById("val-projects").textContent = `${breakdown.projects || 0}%`;

  document.getElementById("recommendation-text").textContent =
    match.recommendation || "We couldn't generate a detailed recommendation for this match.";
}

function animateScoreRing(score) {
  const circle = document.getElementById("score-ring-fill");
  const numberEl = document.getElementById("score-number-value");
  if (!circle) return;

  const circumference = 2 * Math.PI * 90;
  const offset = circumference - (Math.min(Math.max(score, 0), 100) / 100) * circumference;

  requestAnimationFrame(() => {
    circle.style.strokeDashoffset = offset;
  });

  let current = 0;
  const duration = 1000;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    current = Math.round(progress * score);
    numberEl.textContent = current;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function animateBar(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  requestAnimationFrame(() => { el.style.width = `${value}%`; });
}

/* ------------------------------------------------------------
   Boot
   ------------------------------------------------------------ */
document.addEventListener("DOMContentLoaded", () => {
  initHomepage();
  initJobsPage();
  initJobDetailPage();
  initUploadPage();
  initMatchResultPage();
});