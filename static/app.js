const planForm = document.getElementById("plan-form");
const reportForm = document.getElementById("report-form");
const sampleBtn = document.getElementById("sample-btn");
const newAthleteBtn = document.getElementById("new-athlete-btn");
const saveProfileBtn = document.getElementById("save-profile-btn");
const generateBtn = document.getElementById("generate-btn");
const saveReportBtn = document.getElementById("save-report-btn");
const statusPill = document.getElementById("status-pill");
const emptyState = document.getElementById("empty-state");
const planOutput = document.getElementById("plan-output");
const summaryGrid = document.getElementById("summary-grid");
const weeklyPlan = document.getElementById("weekly-plan");
const sessionTemplates = document.getElementById("session-templates");
const parentTemplate = document.getElementById("parent-template");
const recentReports = document.getElementById("recent-reports");
const reportSearchEl = document.getElementById("report-search");
const reportFilterEl = document.getElementById("report-filter");
const reportPaginationEl = document.getElementById("report-pagination");
const saveMessage = document.getElementById("save-message");
const athleteList = document.getElementById("athlete-list");
const athleteSearchEl = document.getElementById("athlete-search");
const parentReportPreview = document.getElementById("parent-report-preview");
const lessonDetail = document.getElementById("lesson-detail");
const authGate = document.getElementById("auth-gate");
const loginForm = document.getElementById("login-form");
const loginUsernameEl = document.getElementById("login-username");
const loginPasswordEl = document.getElementById("login-password");
const loginBtn = document.getElementById("login-btn");
const authMessageEl = document.getElementById("auth-message");
const authRolePill = document.getElementById("auth-role-pill");
const authUserText = document.getElementById("auth-user-text");
const logoutBtn = document.getElementById("logout-btn");

const nameEl = document.getElementById("name");
const traineeGroupEl = document.getElementById("trainee-group");
const ageEl = document.getElementById("age");
const genderEl = document.getElementById("gender");
const trainingTypeEl = document.getElementById("training-type");
const schoolEl = document.getElementById("school");
const gradeEl = document.getElementById("grade");
const heightEl = document.getElementById("height");
const weightEl = document.getElementById("weight");
const guardianNameEl = document.getElementById("guardian-name");
const guardianPhoneEl = document.getElementById("guardian-phone");
const trainingGoalEl = document.getElementById("training-goal");
const cycleWeeksEl = document.getElementById("cycle-weeks");
const sessionsPerWeekEl = document.getElementById("sessions-per-week");
const sessionDurationEl = document.getElementById("session-duration");
const trainingExperienceEl = document.getElementById("training-experience");
const sportPreferenceEl = document.getElementById("sport-preference");
const availableScheduleEl = document.getElementById("available-schedule");
const assessmentEl = document.getElementById("assessment");
const baselineMetricsEl = document.getElementById("baseline-metrics");
const needsEl = document.getElementById("needs");
const medicalHistoryEl = document.getElementById("medical-history");
const injuryHistoryEl = document.getElementById("injury-history");
const constraintsEl = document.getElementById("constraints");
const personalityNotesEl = document.getElementById("personality-notes");

const sessionDateEl = document.getElementById("session-date");
const reportDurationEl = document.getElementById("report-duration");
const engagementEl = document.getElementById("engagement");
const rpeEl = document.getElementById("rpe");
const sessionContentEl = document.getElementById("session-content");
const coachNotesEl = document.getElementById("coach-notes");
const homeworkEl = document.getElementById("homework");
const mediaFilesEl = document.getElementById("media-files");

let bootstrapData = null;
let currentPlan = null;
let currentAthleteId = "";
let selectedLessonId = "";
let currentReport = null;
let authState = { authenticated: false, user: null };
let currentReportPage = 1;
const REPORTS_PER_PAGE = 6;

function formatUpdatedAt(value) {
  return value ? String(value).replace("T", " ") : "刚刚";
}

function isAdmin() {
  return authState?.user?.role === "admin";
}

function setAuthMessage(text, variant = "idle") {
  if (!authMessageEl) return;
  authMessageEl.textContent = text;
  authMessageEl.dataset.variant = variant;
}

function applyAuthState(state) {
  authState = state || { authenticated: false, user: null };
  const authenticated = Boolean(authState.authenticated && authState.user);
  document.body.classList.toggle("locked", !authenticated);
  authGate?.classList.toggle("active", !authenticated);
  authRolePill.textContent = authenticated ? authState.user.role_label || authState.user.role : "未登录";
  authRolePill.dataset.variant = authenticated ? "success" : "idle";
  authUserText.textContent = authenticated
    ? `${authState.user.username} 已登录，当前权限：${authState.user.role_label || authState.user.role} · ${authState.user.store_name || "神兽体育"}`
    : "请先登录后再使用教练工作台。";
  logoutBtn.hidden = !authenticated;
  if (!authenticated) {
    loginPasswordEl.value = "";
    currentPlan = null;
    currentReport = null;
    selectedLessonId = "";
    currentAthleteId = "";
    emptyState.classList.remove("hidden");
    planOutput.classList.add("hidden");
    renderAthleteList([]);
    renderRecentReports([]);
    renderLessonDetail(null);
    renderParentReportPreview(null);
  } else {
    setAuthMessage("登录成功后，系统会自动加载学员和训练数据。", "success");
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function filteredAthletes(items = []) {
  const keyword = athleteSearchEl?.value?.trim().toLowerCase() || "";
  if (!keyword) return items;
  return items.filter((item) => {
    const name = String(item.name || "").toLowerCase();
    const phone = String(item.guardian_phone || "").toLowerCase();
    return name.includes(keyword) || phone.includes(keyword);
  });
}

function filteredReports(items = []) {
  const keyword = reportSearchEl?.value?.trim().toLowerCase() || "";
  const filterValue = reportFilterEl?.value || "all";
  return items.filter((item) => {
    const matchesKeyword =
      !keyword ||
      String(item.athlete_name || "").toLowerCase().includes(keyword) ||
      String(item.goal || "").toLowerCase().includes(keyword) ||
      String(item.date || "").toLowerCase().includes(keyword) ||
      String(item.summary || "").toLowerCase().includes(keyword);
    if (!matchesKeyword) return false;
    if (filterValue === "all") return true;
    if (filterValue === "media") return Number(item.media_count || 0) > 0;
    return String(item.engagement || "") === filterValue;
  });
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) {
      applyAuthState({ authenticated: false, user: null });
      setAuthMessage(data.error || "登录状态已失效，请重新登录。", "error");
    }
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function renderOptions(select, values, formatter = (value) => value) {
  select.innerHTML = values.map((value) => `<option value="${value}">${formatter(value)}</option>`).join("");
}

function setStatus(text, variant = "idle") {
  statusPill.textContent = text;
  statusPill.dataset.variant = variant;
}

function athletePayload() {
  return {
    athlete_id: currentAthleteId,
    name: nameEl.value.trim(),
    trainee_group: traineeGroupEl.value,
    age: Number(ageEl.value),
    gender: genderEl.value,
    training_type: trainingTypeEl.value,
    school: schoolEl.value.trim(),
    grade: gradeEl.value.trim(),
    height: heightEl.value.trim(),
    weight: weightEl.value.trim(),
    guardian_name: guardianNameEl.value.trim(),
    guardian_phone: guardianPhoneEl.value.trim(),
    training_goal: trainingGoalEl.value,
    cycle_weeks: Number(cycleWeeksEl.value),
    sessions_per_week: Number(sessionsPerWeekEl.value),
    session_duration_min: Number(sessionDurationEl.value),
    training_experience: trainingExperienceEl.value.trim(),
    sport_preference: sportPreferenceEl.value.trim(),
    available_schedule: availableScheduleEl.value.trim(),
    assessment: assessmentEl.value.trim(),
    baseline_metrics: baselineMetricsEl.value.trim(),
    needs: needsEl.value.trim(),
    medical_history: medicalHistoryEl.value.trim(),
    injury_history: injuryHistoryEl.value.trim(),
    constraints: constraintsEl.value.trim(),
    personality_notes: personalityNotesEl.value.trim(),
  };
}

function applyProfile(profile) {
  currentAthleteId = profile.id || "";
  nameEl.value = profile.name || "";
  traineeGroupEl.value = profile.trainee_group || bootstrapData?.trainee_groups?.[1] || "青少年";
  ageEl.value = profile.age || 10;
  genderEl.value = profile.gender || "未说明";
  trainingTypeEl.value = profile.training_type || "私教课";
  schoolEl.value = profile.school || "";
  gradeEl.value = profile.grade || "";
  heightEl.value = profile.height || "";
  weightEl.value = profile.weight || "";
  guardianNameEl.value = profile.guardian_name || "";
  guardianPhoneEl.value = profile.guardian_phone || "";
  trainingGoalEl.value = profile.training_goal || bootstrapData.goals[0];
  cycleWeeksEl.value = profile.cycle_weeks || bootstrapData.cycles[0];
  sessionsPerWeekEl.value = profile.sessions_per_week || bootstrapData.frequencies[0];
  sessionDurationEl.value = profile.session_duration_min || bootstrapData.durations[0];
  reportDurationEl.value = profile.session_duration_min || bootstrapData.durations[0];
  trainingExperienceEl.value = profile.training_experience || "";
  sportPreferenceEl.value = profile.sport_preference || "";
  availableScheduleEl.value = profile.available_schedule || "";
  assessmentEl.value = profile.assessment || "";
  baselineMetricsEl.value = profile.baseline_metrics || "";
  needsEl.value = profile.needs || "";
  medicalHistoryEl.value = profile.medical_history || "";
  injuryHistoryEl.value = profile.injury_history || "";
  constraintsEl.value = profile.constraints || "";
  personalityNotesEl.value = profile.personality_notes || "";
  syncAgeBoundsByGroup();
}

function fillSample() {
  const sample = bootstrapData?.sample_profiles?.[0];
  if (!sample) return;
  currentAthleteId = "";
  applyProfile({
    id: "",
    name: sample.name,
    trainee_group: sample.trainee_group || "青少年",
    age: sample.age,
    gender: sample.gender,
    training_type: sample.training_type,
    school: "",
    grade: "",
    height: "",
    weight: "",
    guardian_name: "",
    guardian_phone: "",
    training_goal: sample.training_goal,
    cycle_weeks: sample.cycle_weeks,
    sessions_per_week: sample.sessions_per_week,
    session_duration_min: sample.session_duration_min,
    training_experience: "有基础运动参与经历，但缺少系统训练记录。",
    sport_preference: "喜欢跑跳类和趣味性项目。",
    available_schedule: "平日晚间和周末上午可安排训练。",
    assessment: sample.assessment,
    baseline_metrics: "",
    needs: sample.needs,
    medical_history: "",
    injury_history: "",
    constraints: sample.constraints,
    personality_notes: "课堂中适合通过鼓励和游戏化形式提高投入度。",
  });
}

function startNewAthlete() {
  currentAthleteId = "";
  applyProfile({
    id: "",
    name: "",
    trainee_group: bootstrapData?.trainee_groups?.[1] || "青少年",
    age: 10,
    gender: "男",
    training_type: bootstrapData?.training_types?.[0] || "私教课",
    school: "",
    grade: "",
    height: "",
    weight: "",
    guardian_name: "",
    guardian_phone: "",
    training_goal: bootstrapData?.goals?.[0] || "青少年体适能启蒙",
    cycle_weeks: bootstrapData?.cycles?.[0] || 4,
    sessions_per_week: bootstrapData?.frequencies?.[0] || 2,
    session_duration_min: bootstrapData?.durations?.[0] || 60,
    training_experience: "",
    sport_preference: "",
    available_schedule: "",
    assessment: "",
    baseline_metrics: "",
    needs: "",
    medical_history: "",
    injury_history: "",
    constraints: "",
    personality_notes: "",
  });
  renderAthleteList(bootstrapData?.athlete_profiles || []);
  setStatus("已切换到新建学员", "success");
}

function syncAgeBoundsByGroup() {
  const group = traineeGroupEl.value;
  if (group === "幼儿") {
    ageEl.min = "3";
    ageEl.max = "6";
    if (Number(ageEl.value) < 3 || Number(ageEl.value) > 6) ageEl.value = 5;
    return;
  }
  if (group === "青少年") {
    ageEl.min = "7";
    ageEl.max = "16";
    if (Number(ageEl.value) < 7 || Number(ageEl.value) > 16) ageEl.value = 10;
    return;
  }
  ageEl.min = "17";
  ageEl.max = "80";
  if (Number(ageEl.value) < 17) ageEl.value = 18;
}

function renderAthleteList(items = []) {
  const visibleItems = filteredAthletes(items);
  const deleteAction = isAdmin()
    ? (item) => `<button class="card-delete-btn" type="button" data-delete-athlete-id="${item.id}" aria-label="删除 ${item.name} 档案">删除</button>`
    : () => "";

  if (items.length && !visibleItems.length) {
    athleteList.innerHTML = `<div class="recent-empty">没有找到匹配的会员，请尝试输入其他姓名或家长手机号。</div>`;
    return;
  }

  if (!items.length) {
    athleteList.innerHTML = `<div class="recent-empty">还没有保存的学员档案，先在右侧填写资料后点击“保存档案”。</div>`;
    return;
  }

  athleteList.innerHTML = visibleItems
    .map(
      (item) => `
        <article class="athlete-card-shell ${item.id === currentAthleteId ? "active" : ""}">
          <button class="athlete-card select-athlete ${item.id === currentAthleteId ? "active" : ""}" type="button" data-id="${item.id}">
            <div class="athlete-card-top">
              <strong>${item.name}</strong>
              <span>${item.trainee_group || "青少年"} · ${item.age} 岁 · ${item.gender}</span>
            </div>
            <p>${item.goal || "目标待补充"} · ${item.training_type || "课程类型待补充"}</p>
            <small>家长 ${item.guardian_phone || "未填写"} · ${item.session_duration_min || 60} 分钟课 · 更新于 ${formatUpdatedAt(item.updated_at)}</small>
          </button>
          ${deleteAction(item)}
        </article>
      `,
    )
    .join("");
}

function renderSummary(plan) {
  const { athlete, summary, plan_overview } = plan;
  const cards = [
    { label: "学员分层", value: plan_overview.framework_label || athlete.band, meta: `${athlete.trainee_group || "青少年"} · ${athlete.age} 岁 · ${athlete.gender}` },
    { label: "训练目标", value: athlete.goal, meta: athlete.training_type },
    { label: "周期安排", value: `${plan_overview.cycle_weeks} 周`, meta: `每周 ${plan_overview.sessions_per_week} 课` },
    { label: "单次课时", value: `${plan_overview.session_duration_min} 分钟`, meta: "模板已按时长填满" },
  ];

  summaryGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="summary-card">
          <span>${card.label}</span>
          <strong>${card.value}</strong>
          <p>${card.meta}</p>
        </article>
      `,
    )
    .join("");

  summaryGrid.innerHTML += `
    <article class="summary-wide">
      <h3>训练需求与教练抓手</h3>
      <p><strong>年龄框架：</strong>${athlete.age_framework || plan_overview.framework_label || athlete.band}</p>
      <p><strong>周期逻辑：</strong>${summary.periodisation_logic || "按年龄特点与目标阶段逐周推进。"}</p>
      <p><strong>重点能力：</strong>${(plan_overview.framework_points || []).join("、") || "基础动作、协调、体能与恢复"}</p>
      <p><strong>需求：</strong>${summary.training_needs}</p>
      <p><strong>评估：</strong>${summary.assessment}</p>
      <p><strong>训练经历：</strong>${summary.training_background}</p>
      <p><strong>基础数据：</strong>${summary.baseline_metrics}</p>
      <p><strong>健康提示：</strong>${summary.health_notes}</p>
      <p><strong>时间安排：</strong>${summary.schedule_notes}</p>
      <p><strong>限制：</strong>${summary.constraints}</p>
      <p><strong>教练抓手：</strong>${summary.coach_takeaway}</p>
    </article>
  `;
}

function renderWeeklyPlan(plan) {
  weeklyPlan.innerHTML = plan.weekly_plan_detailed
    .map(
      (week) => `
        <article class="week-card">
          <div class="week-head">
            <strong>第 ${week.week} 周</strong>
            <span>${week.focus}</span>
          </div>
          <div class="week-sessions">
            ${week.sessions
              .map(
                (item) => `
                  <button class="micro-card lesson-trigger ${item.id === selectedLessonId ? "active" : ""}" type="button" data-lesson-id="${item.id}">
                    <h4>${item.title}</h4>
                    <p>${item.blocks.map((block) => block.title).join(" + ")}</p>
                    <small>${item.focus} · ${item.theme_track || "标准课"} · ${item.session_variant || "标准推进"} · ${item.intensity_target}</small>
                    <small>${item.storyline || ""}</small>
                    <div class="micro-note">${item.coach_summary}</div>
                  </button>
                `,
              )
              .join("")}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderLessonDetail(lesson) {
  if (!lesson) {
    lessonDetail.className = "lesson-detail empty-state";
    lessonDetail.innerHTML = "从上方每周计划中选择一节课，这里会显示完整训练内容。";
    return;
  }

  lessonDetail.className = "lesson-detail";
  lessonDetail.innerHTML = `
    <article class="lesson-print-card" id="lesson-print-card">
      <div class="lesson-detail-top">
        <div>
          <span class="report-badge">单节课教案</span>
          <h3>${lesson.title}</h3>
          <p>${currentPlan.athlete.name} · ${currentPlan.athlete.goal} · ${lesson.duration_label}</p>
        </div>
        <button id="print-lesson-btn" class="ghost accent-ghost" type="button">打印这节课</button>
      </div>
      <div class="tag-row lesson-tags">
        <span>${lesson.focus}</span>
        <span>${lesson.theme_track || "标准课"}</span>
        <span>${lesson.session_variant || "标准推进"}</span>
        <span>${lesson.intensity_target}</span>
        <span>${lesson.coach_summary}</span>
      </div>
      <div class="coach-tip">${lesson.storyline || ""}</div>
      <div class="lesson-grid">
        <div><label>器材清单</label><span>${(lesson.equipment || []).join("、") || "按课堂准备常规器材"}</span></div>
        <div><label>教练口令</label><span>${(lesson.coach_cues || []).join("；") || "先讲规则，再开始练习。"}</span></div>
      </div>
      <div class="lesson-block-list">
        ${lesson.blocks
          .map(
            (block) => `
              <div class="lesson-block-card">
                <div class="lesson-block-head">
                  <strong>${block.title}</strong>
                  <span>模块 ${block.order} · ${block.phase} · ${block.time_range || block.duration_label} · ${block.level_label}</span>
                </div>
                <p>${block.description}</p>
                <div class="lesson-grid">
                  <div><label>执行时段</label><span>${block.time_range || block.duration_label}</span></div>
                  <div><label>动作要求</label><span>${block.cues}</span></div>
                  <div><label>组数 / 次数</label><span>${block.sets_reps}</span></div>
                  <div><label>间歇要求</label><span>${block.rest}</span></div>
                  <div><label>强度要求</label><span>${block.intensity}</span></div>
                  <div><label>本节目标</label><span>${block.target_outcome}</span></div>
                  <div><label>安全提示</label><span>${block.safety}</span></div>
                  <div><label>降阶版</label><span>${block.regression}</span></div>
                  <div><label>标准版</label><span>${block.standard}</span></div>
                  <div><label>进阶版</label><span>${block.progression}</span></div>
                </div>
                <div class="coach-tip">${block.coach_tip}</div>
              </div>
            `,
          )
          .join("")}
      </div>
    </article>
  `;
}

function buildPrintWindowHtml(lesson, athlete) {
  const printDate = sessionDateEl?.value || new Date().toLocaleDateString("zh-CN");
  const guardianLine = athlete.guardian_name || athlete.guardian_phone
    ? `${athlete.guardian_name || "家长"} ${athlete.guardian_phone || ""}`.trim()
    : "待补充";
  const schoolLine = [athlete.school, athlete.grade].filter(Boolean).join(" / ") || "待补充";
  const brandLogoUrl = `${window.location.origin}/static/brand-logo-circle.png`;
  const blockHtml = lesson.blocks
    .map(
      (block) => `
        <article class="print-block">
          <div class="print-block-head">
            <h3>${escapeHtml(block.title)}</h3>
            <span>模块 ${escapeHtml(String(block.order || ""))} / ${escapeHtml(block.phase)} / ${escapeHtml(block.time_range || block.duration_label)} / ${escapeHtml(block.level_label || "标准版")}</span>
          </div>
          <p class="print-desc">${escapeHtml(block.description)}</p>
          <div class="print-grid">
            <div><label>执行时段</label><p>${escapeHtml(block.time_range || block.duration_label)}</p></div>
            <div><label>动作要求</label><p>${escapeHtml(block.cues)}</p></div>
            <div><label>组数 / 次数</label><p>${escapeHtml(block.sets_reps)}</p></div>
            <div><label>间歇要求</label><p>${escapeHtml(block.rest)}</p></div>
            <div><label>强度要求</label><p>${escapeHtml(block.intensity)}</p></div>
            <div><label>本节目标</label><p>${escapeHtml(block.target_outcome || "完成本节核心任务")}</p></div>
            <div><label>安全提示</label><p>${escapeHtml(block.safety || "动作稳定优先于数量")}</p></div>
            <div><label>降阶版</label><p>${escapeHtml(block.regression || "降低难度后完成动作")}</p></div>
            <div><label>标准版</label><p>${escapeHtml(block.standard || block.prescription || "按标准要求执行")}</p></div>
            <div><label>进阶版</label><p>${escapeHtml(block.progression || "动作稳定后逐步增加难度")}</p></div>
          </div>
          <div class="print-tip"><strong>教练提示：</strong>${escapeHtml(block.coach_tip)}</div>
        </article>
      `,
    )
    .join("");

  return `<!DOCTYPE html>
  <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>${escapeHtml(lesson.title)} 打印教案</title>
      <style>
        @page { size: A4 portrait; margin: 10mm; }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: "PingFang SC", "Noto Sans SC", sans-serif;
          color: #172b3c;
          background: #fff;
        }
        .sheet {
          width: 190mm;
          min-height: 277mm;
          margin: 0 auto;
          padding: 3mm 2mm 2mm;
        }
        .brand-shell {
          display: grid;
          grid-template-columns: 42mm 1fr;
          gap: 4mm;
          margin-bottom: 4mm;
        }
        .brand-aside {
          min-height: 72mm;
          padding: 5mm 4mm;
          border-radius: 4mm;
          background: #f36c22;
          color: #fff;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .brand-aside-top {
          display: grid;
          gap: 3mm;
        }
        .brand-logo-dot {
          width: 18mm;
          height: 18mm;
          display: block;
        }
        .brand-logo-dot svg {
          display: block;
          width: 100%;
          height: 100%;
        }
        .brand-logo-dot img {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: contain;
        }
        .brand-code {
          font-size: 17pt;
          font-weight: 800;
          line-height: 1;
          color: #fff;
        }
        .brand-aside-text {
          font-size: 8.2pt;
          line-height: 1.6;
          color: rgba(255, 255, 255, 0.96);
        }
        .brand {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 8mm;
          padding: 3.5mm;
          border: 1px solid #d8e2ea;
          border-radius: 4mm;
          background: linear-gradient(180deg, #fff 0%, #fbfcfd 100%);
        }
        .brand-tag {
          display: inline-block;
          padding: 1.5mm 3mm;
          border-radius: 999px;
          background: #fff2eb;
          color: #f36c22;
          font-size: 9pt;
          font-weight: 700;
          margin-bottom: 2mm;
        }
        .brand-mark {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 18mm;
          height: 18mm;
          border-radius: 50%;
          background: #f36c22;
          color: #fff;
          font-size: 11pt;
          font-weight: 800;
          margin-bottom: 2.5mm;
        }
        .brand-subtitle {
          margin-top: 1.5mm;
          color: #4f433d;
          font-size: 8.8pt;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        h1 {
          margin: 0;
          font-size: 18.5pt;
          line-height: 1.28;
          color: #112535;
        }
        .sub {
          margin-top: 2mm;
          color: #587184;
          font-size: 10pt;
          line-height: 1.5;
        }
        .meta {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 2mm;
          min-width: 72mm;
        }
        .meta-item {
          padding: 2.5mm;
          border: 1px solid #d8e2ea;
          border-radius: 3mm;
          background: #f8fbfd;
        }
        .meta-item label {
          display: block;
          color: #6d8191;
          font-size: 8pt;
          margin-bottom: 1mm;
        }
        .meta-item p {
          margin: 0;
          font-size: 9.5pt;
          line-height: 1.45;
        }
        .summary {
          display: flex;
          flex-wrap: wrap;
          gap: 2mm;
          margin: 0 0 4mm;
        }
        .summary span {
          padding: 1.5mm 3mm;
          border-radius: 999px;
          background: #eef4f8;
          color: #243f56;
          font-size: 8.5pt;
        }
        .notes-bar {
          margin-bottom: 4mm;
          padding: 2.5mm 3mm;
          border-radius: 3mm;
          border: 1px solid #e3ebf1;
          background: #fafcfd;
        }
        .notes-bar label {
          display: block;
          margin-bottom: 1mm;
          color: #6d8191;
          font-size: 8pt;
        }
        .notes-bar p {
          margin: 0;
          color: #23384d;
          font-size: 8.8pt;
          line-height: 1.5;
        }
        .blocks {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 3mm;
        }
        .print-block {
          border: 1px solid #d8e2ea;
          border-radius: 4mm;
          padding: 3mm;
          break-inside: avoid;
          page-break-inside: avoid;
        }
        .print-block-head {
          display: flex;
          justify-content: space-between;
          gap: 3mm;
          margin-bottom: 2mm;
        }
        .print-block-head h3 {
          margin: 0;
          font-size: 11pt;
          line-height: 1.3;
        }
        .print-block-head span {
          color: #587184;
          font-size: 8.5pt;
          white-space: nowrap;
        }
        .print-desc, .print-tip {
          font-size: 8.8pt;
          line-height: 1.5;
          margin: 0;
        }
        .print-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 2mm;
          margin: 2.5mm 0;
        }
        .print-grid div {
          padding: 2mm;
          border-radius: 2.5mm;
          background: #f8fbfd;
          border: 1px solid #e3ebf1;
        }
        .print-grid label {
          display: block;
          margin-bottom: 1mm;
          color: #6d8191;
          font-size: 7.8pt;
        }
        .print-grid p {
          margin: 0;
          font-size: 8.5pt;
          line-height: 1.45;
        }
        .print-tip {
          color: #1d3a52;
          background: #edf7f5;
          border-radius: 2.5mm;
          padding: 2mm;
        }
        .summary {
          align-items: center;
        }
        .footer {
          display: grid;
          grid-template-columns: 1.2fr 0.8fr;
          gap: 4mm;
          margin-top: 4mm;
        }
        .footer-card {
          min-height: 24mm;
          padding: 3mm;
          border: 1px solid #d8e2ea;
          border-radius: 4mm;
          background: #fff;
        }
        .footer-card label {
          display: block;
          margin-bottom: 1.5mm;
          color: #6d8191;
          font-size: 8pt;
        }
        .footer-line {
          margin-top: 10mm;
          display: flex;
          justify-content: space-between;
          gap: 4mm;
          color: #2f465b;
          font-size: 8.8pt;
        }
      </style>
    </head>
    <body>
      <main class="sheet">
        <section class="brand-shell">
          <aside class="brand-aside">
            <div class="brand-aside-top">
              <div class="brand-logo-dot"><img src="${brandLogoUrl}" alt="神兽体育圆形logo" /></div>
              <div class="brand-code">神兽体育</div>
              <div class="brand-aside-text">
                青少年体适能训练<br />
                会员课件系统<br />
                与报告平台
              </div>
            </div>
            <div class="brand-aside-text">
              MYTHICAL<br />
              CREATURES SPORTS
            </div>
          </aside>
        <section class="brand">
          <div>
            <span class="brand-tag">神兽体育训练教案</span>
            <h1>${escapeHtml(lesson.title)}</h1>
            <div class="brand-subtitle">MYTHICAL CREATURES SPORTS</div>
            <p class="sub">${escapeHtml(athlete.name)} · ${escapeHtml(athlete.goal)} · ${escapeHtml(lesson.duration_label)}</p>
            </div>
            <div class="meta">
              <div class="meta-item"><label>学员</label><p>${escapeHtml(athlete.name)}</p></div>
              <div class="meta-item"><label>年龄</label><p>${escapeHtml(athlete.age)} 岁</p></div>
              <div class="meta-item"><label>课程焦点</label><p>${escapeHtml(lesson.focus)}</p></div>
              <div class="meta-item"><label>整体强度</label><p>${escapeHtml(lesson.intensity_target)}</p></div>
              <div class="meta-item"><label>课程日期</label><p>${escapeHtml(printDate)}</p></div>
              <div class="meta-item"><label>学校 / 年级</label><p>${escapeHtml(schoolLine)}</p></div>
              <div class="meta-item"><label>家长联系</label><p>${escapeHtml(guardianLine)}</p></div>
              <div class="meta-item"><label>训练类型</label><p>${escapeHtml(athlete.training_type || "会员课")}</p></div>
            </div>
          </section>
        </section>
        <div class="summary">
          <span>${escapeHtml(lesson.coach_summary)}</span>
          <span>${escapeHtml(lesson.theme_track || "标准课")} / ${escapeHtml(lesson.session_variant || "标准推进")}</span>
          <span>${escapeHtml(athlete.age_framework || athlete.band || "青少年训练框架")}</span>
          <span>打印时间：${escapeHtml(new Date().toLocaleDateString("zh-CN"))}</span>
        </div>
        <section class="notes-bar">
          <label>课前提醒</label>
          <p>${escapeHtml(lesson.storyline || "到课前完成饮水、鞋带与装备检查，课程中优先保证动作质量与课堂秩序。")}</p>
        </section>
        <section class="notes-bar">
          <label>器材与口令</label>
          <p>器材：${escapeHtml((lesson.equipment || []).join("、") || "常规课堂器材")} / 口令：${escapeHtml((lesson.coach_cues || []).join("；") || "先讲规则再开始训练。")}</p>
        </section>
        <section class="blocks">${blockHtml}</section>
        <section class="footer">
          <div class="footer-card">
            <label>课后备注区</label>
            <p>1. 本节课重点完成情况：</p>
            <p>2. 需要家长配合的家庭练习：</p>
            <p>3. 下节课重点跟进内容：</p>
          </div>
          <div class="footer-card">
            <label>签字确认</label>
            <div class="footer-line">
              <span>教练签名：________________</span>
            </div>
            <div class="footer-line">
              <span>家长签名：________________</span>
            </div>
          </div>
        </section>
      </main>
    </body>
  </html>`;
}

function openPrintWindowForLesson(lesson) {
  if (!lesson || !currentPlan?.athlete) return;
  const html = buildPrintWindowHtml(lesson, currentPlan.athlete);
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const printUrl = URL.createObjectURL(blob);
  const printWindow = window.open(printUrl, "_blank", "width=1100,height=900");
  if (!printWindow) {
    setStatus("浏览器拦截了打印窗口，请允许弹窗后重试", "error");
    return;
  }
  printWindow.focus();

  const triggerPrint = () => {
    printWindow.focus();
    printWindow.print();
    setTimeout(() => URL.revokeObjectURL(printUrl), 1500);
  };

  printWindow.addEventListener("load", () => setTimeout(triggerPrint, 200), { once: true });
}

function renderSessionTemplates(plan) {
  sessionTemplates.innerHTML = plan.session_templates
    .map(
      (session) => `
        <article class="session-card">
          <div class="session-top">
            <div>
              <strong>${session.session_name}</strong>
              <span>${session.focus} · ${session.theme_track || "标准课"} · ${session.session_variant || "标准推进"}</span>
            </div>
            <em>${session.duration_label}</em>
          </div>
          <p class="session-brief">${session.coach_brief}</p>
          <div class="coach-tip">${session.storyline || ""}</div>
          <div class="coach-tip">器材：${(session.equipment || []).join("、") || "常规课堂器材"} / 口令：${(session.coach_cues || []).join("；") || "先规则后执行"}</div>
          <div class="session-blocks">
            ${session.blocks
              .map(
                (block) => `
                  <div class="drill-card">
                    <div class="drill-head">
                      <span>模块 ${block.order} · ${block.phase} · ${block.time_range || block.duration_label} · ${block.level_label}</span>
                      <strong>${block.title}</strong>
                    </div>
                    <p>${block.description}</p>
                    <small>执行时段：${block.time_range || block.duration_label}</small>
                    <small>动作要求：${block.cues}</small>
                    <small>训练安排：${block.prescription}</small>
                    <small>强度建议：${block.intensity}</small>
                    <small>训练目标：${block.target_outcome}</small>
                    <div class="coach-tip">${block.coach_tip}</div>
                    <div class="coach-tip">降阶：${block.regression}</div>
                    <div class="coach-tip">标准：${block.standard}</div>
                    <div class="coach-tip">进阶：${block.progression}</div>
                    <div class="video-links">
                      ${block.videos
                        .map(
                          (video) => `
                            <a href="${video.url}" target="_blank" rel="noopener noreferrer">${video.label}</a>
                          `,
                        )
                        .join("")}
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderParentTemplate(plan) {
  const template = plan.parent_report_template;
  parentTemplate.innerHTML = `
    <article class="parent-card">
      <h3>${template.title}</h3>
      <p class="parent-headline">${template.headline}</p>
      <div class="parent-points">
        ${template.highlights.map((item) => `<p>${item}</p>`).join("")}
      </div>
      <div class="parent-homework">
        <span>家庭练习建议</span>
        <p>${template.homework}</p>
      </div>
    </article>
  `;
}

function buildLessonContentText(lesson) {
  return (lesson?.blocks || [])
    .map((block) => `${block.time_range} ${block.phase}：${block.title}（${block.sets_reps}，间歇 ${block.rest}，强度 ${block.intensity}）`)
    .join("；");
}

function applyLessonToReportDraft(lesson) {
  if (!lesson) return;
  reportDurationEl.value = String(lesson.duration_min || currentPlan?.plan_overview?.session_duration_min || reportDurationEl.value);
  sessionContentEl.value = buildLessonContentText(lesson);
  if (!coachNotesEl.value.trim()) {
    coachNotesEl.value = lesson.coach_summary || "";
  }
  if (!homeworkEl.value.trim()) {
    homeworkEl.value = currentPlan?.parent_report_template?.homework || "";
  }
}

function renderReportPagination(totalItems = 0) {
  if (!reportPaginationEl) return;
  if (totalItems <= REPORTS_PER_PAGE) {
    reportPaginationEl.innerHTML = "";
    return;
  }
  const totalPages = Math.max(1, Math.ceil(totalItems / REPORTS_PER_PAGE));
  currentReportPage = Math.min(currentReportPage, totalPages);
  reportPaginationEl.innerHTML = `
    <button class="ghost pagination-btn" type="button" data-report-page="${currentReportPage - 1}" ${currentReportPage <= 1 ? "disabled" : ""}>上一页</button>
    <span class="pagination-meta">第 ${currentReportPage} / ${totalPages} 页，共 ${totalItems} 份报告</span>
    <button class="ghost pagination-btn" type="button" data-report-page="${currentReportPage + 1}" ${currentReportPage >= totalPages ? "disabled" : ""}>下一页</button>
  `;
}

function renderRecentReports(items = []) {
  const deleteAction = isAdmin()
    ? (item) => `<button class="card-delete-btn" type="button" data-delete-report-id="${item.id}" aria-label="删除 ${item.athlete_name} 的训练报告">删除</button>`
    : () => "";
  const filtered = filteredReports(items);
  if (!items.length) {
    recentReports.innerHTML = `<div class="recent-empty">还没有保存的训练报告，完成一次课后记录后会显示在这里。</div>`;
    renderReportPagination(0);
    return;
  }
  if (!filtered.length) {
    recentReports.innerHTML = `<div class="recent-empty">没有找到匹配的训练报告，请换一个搜索词或筛选条件。</div>`;
    renderReportPagination(0);
    return;
  }
  const totalPages = Math.max(1, Math.ceil(filtered.length / REPORTS_PER_PAGE));
  currentReportPage = Math.min(currentReportPage, totalPages);
  const start = (currentReportPage - 1) * REPORTS_PER_PAGE;
  const visibleItems = filtered.slice(start, start + REPORTS_PER_PAGE);
  recentReports.innerHTML = visibleItems
    .map(
      (item) => `
        <article class="recent-card ${currentReport?.id === item.id ? "active" : ""}" data-report-id="${item.id}">
          <div class="recent-top">
            <div>
              <strong>${item.athlete_name}</strong>
              <span>${item.date || "待补充日期"}</span>
            </div>
            ${deleteAction(item)}
          </div>
          <p>${item.goal || "训练目标待补充"}</p>
          <small>${item.summary || "本次已记录训练表现。"} · 投入度 ${item.engagement || "良好"} · 素材 ${item.media_count || 0} 个</small>
        </article>
      `,
    )
    .join("");
  renderReportPagination(filtered.length);
}

function buildTrendSvg(points = []) {
  if (!points.length) return "";
  const width = 560;
  const height = 180;
  const paddingX = 36;
  const paddingY = 24;
  const minScore = 40;
  const maxScore = 100;
  const stepX = points.length === 1 ? 0 : (width - paddingX * 2) / (points.length - 1);
  const coords = points.map((point, index) => {
    const x = paddingX + stepX * index;
    const ratio = (point.score - minScore) / (maxScore - minScore);
    const y = height - paddingY - ratio * (height - paddingY * 2);
    return { ...point, x, y };
  });
  const path = coords.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  return `
    <svg viewBox="0 0 ${width} ${height}" class="progress-trend-svg" role="img" aria-label="训练进展趋势图">
      <line x1="${paddingX}" y1="${height - paddingY}" x2="${width - paddingX}" y2="${height - paddingY}" stroke="rgba(71,58,52,0.18)" stroke-width="2" />
      <path d="${path}" fill="none" stroke="#ef6a2e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
      ${coords.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="5" fill="#ef6a2e" />`).join("")}
      ${coords
        .map(
          (point) => `
            <text x="${point.x}" y="${height - 6}" text-anchor="middle" font-size="12" fill="#7a665c">${point.label}</text>
            <text x="${point.x}" y="${point.y - 10}" text-anchor="middle" font-size="12" fill="#473a34">${point.score}</text>
          `,
        )
        .join("")}
    </svg>
  `;
}

function buildGoalRingSvg(score = 0) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - progress / 100);
  return `
    <svg viewBox="0 0 140 140" class="goal-ring-svg" role="img" aria-label="周期目标完成度">
      <circle cx="70" cy="70" r="${radius}" fill="none" stroke="rgba(71,58,52,0.08)" stroke-width="12"></circle>
      <circle cx="70" cy="70" r="${radius}" fill="none" stroke="#ef6a2e" stroke-width="12" stroke-linecap="round"
        stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" transform="rotate(-90 70 70)"></circle>
      <text x="70" y="64" text-anchor="middle" font-size="15" fill="#7a665c">完成度</text>
      <text x="70" y="86" text-anchor="middle" font-size="26" font-weight="700" fill="#241d19">${progress}%</text>
    </svg>
  `;
}

function buildParentShareHtml(report) {
  const progressChart = report.parent_friendly.progress_chart || { dimensions: [], trend: [], overall_score: 0 };
  const brandLogoUrl = `${window.location.origin}/static/brand-logo-circle.png`;
  const dimensionHtml = (progressChart.dimensions || [])
    .map(
      (item) => `
        <div class="share-progress-item">
          <div class="share-progress-top">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(String(item.score))} 分</span>
          </div>
          <div class="share-progress-track"><div class="share-progress-fill" style="width:${item.score}%;"></div></div>
          <small>${escapeHtml(item.status)} ${item.delta >= 0 ? "+" : ""}${escapeHtml(String(item.delta))}</small>
        </div>
      `,
    )
    .join("");
  const mediaHtml = (report.media || [])
    .slice(0, 6)
    .map((item) => {
      if (item.kind === "video") {
        return `
          <figure class="share-media-card">
            <div class="share-video-badge">短视频</div>
            <figcaption>${escapeHtml(item.name)}</figcaption>
          </figure>
        `;
      }
      return `
        <figure class="share-media-card">
          <img src="${item.url}" alt="${escapeHtml(item.name)}" />
          <figcaption>${escapeHtml(item.name)}</figcaption>
        </figure>
      `;
    })
    .join("");
  return `<!DOCTYPE html>
  <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>${escapeHtml(report.athlete.name)} 训练汇报长图</title>
      <style>
        * { box-sizing: border-box; }
        body {
          margin: 0;
          background: linear-gradient(180deg, #fff4ec 0%, #fffaf6 36%, #fff 100%);
          font-family: "PingFang SC", "Noto Sans SC", sans-serif;
          color: #2d231d;
        }
        .share-page {
          width: min(920px, 100%);
          margin: 0 auto;
          padding: 28px 18px 42px;
        }
        .share-sheet {
          overflow: hidden;
          border-radius: 32px;
          border: 1px solid rgba(239, 106, 46, 0.16);
          background: #fffdfa;
          box-shadow: 0 24px 60px rgba(130, 88, 61, 0.14);
        }
        .share-hero {
          position: relative;
          padding: 28px;
          background:
            radial-gradient(circle at top right, rgba(255, 196, 150, 0.44), transparent 24%),
            linear-gradient(135deg, #ef6a2e 0%, #ff8a3d 54%, #ffb067 100%);
          color: #fff;
        }
        .share-brand {
          display: flex;
          align-items: center;
          gap: 14px;
          margin-bottom: 18px;
        }
        .share-brand img {
          width: 54px;
          height: 54px;
          object-fit: contain;
        }
        .share-brand-text strong {
          display: block;
          font-size: 26px;
          line-height: 1.1;
        }
        .share-brand-text span {
          display: block;
          margin-top: 4px;
          font-size: 12px;
          letter-spacing: 0.14em;
          opacity: 0.92;
        }
        .share-hero h1 {
          margin: 0;
          font-size: clamp(28px, 5vw, 42px);
          line-height: 1.18;
        }
        .share-hero p {
          margin: 12px 0 0;
          font-size: 16px;
          line-height: 1.8;
          color: rgba(255,255,255,0.92);
        }
        .share-body {
          padding: 22px;
          display: grid;
          gap: 18px;
        }
        .share-grid,
        .share-metrics,
        .share-two-col,
        .share-media-grid {
          display: grid;
          gap: 14px;
        }
        .share-grid {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .share-metrics {
          grid-template-columns: minmax(180px, 0.42fr) minmax(0, 1fr);
        }
        .share-two-col {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .share-media-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .share-card {
          border-radius: 24px;
          border: 1px solid rgba(71, 58, 52, 0.08);
          background: rgba(255,255,255,0.96);
          padding: 18px;
        }
        .share-card h2 {
          margin: 0 0 10px;
          font-size: 22px;
        }
        .share-card h3 {
          margin: 0 0 10px;
          font-size: 18px;
        }
        .share-mini {
          padding: 16px;
        }
        .share-mini span,
        .share-card p,
        .share-card li,
        .share-card small,
        .share-card figcaption {
          color: #7a665c;
        }
        .share-mini strong {
          display: block;
          margin-top: 8px;
          font-size: 24px;
          color: #241d19;
        }
        .share-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 14px;
        }
        .share-tags span {
          padding: 8px 12px;
          border-radius: 999px;
          background: rgba(255,255,255,0.18);
          border: 1px solid rgba(255,255,255,0.2);
          font-size: 13px;
        }
        .share-score {
          display: grid;
          gap: 8px;
          align-content: start;
          background: linear-gradient(160deg, rgba(239, 106, 46, 0.1), transparent 46%), #fff;
        }
        .share-score strong {
          font-size: 52px;
          line-height: 1;
        }
        .share-progress-list {
          display: grid;
          gap: 12px;
        }
        .share-progress-top {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 6px;
        }
        .share-progress-track {
          height: 10px;
          border-radius: 999px;
          background: rgba(71,58,52,0.08);
          overflow: hidden;
          margin-bottom: 6px;
        }
        .share-progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #ef6a2e 0%, #ffb067 100%);
        }
        .share-ring-wrap {
          display: grid;
          justify-items: center;
        }
        .share-trend svg,
        .share-ring-wrap svg {
          width: 100%;
          height: auto;
          display: block;
        }
        .share-list {
          margin: 0;
          padding-left: 18px;
          display: grid;
          gap: 8px;
        }
        .share-callout {
          padding: 14px 16px;
          border-radius: 18px;
          background: rgba(239, 106, 46, 0.08);
          color: #473a34;
          line-height: 1.8;
        }
        .share-media-card {
          overflow: hidden;
          border-radius: 18px;
          border: 1px solid rgba(71,58,52,0.08);
          background: #fff;
          position: relative;
          min-height: 150px;
        }
        .share-media-card img {
          width: 100%;
          height: 150px;
          object-fit: cover;
          display: block;
        }
        .share-media-card figcaption {
          padding: 10px 12px;
          font-size: 13px;
        }
        .share-video-badge {
          display: grid;
          place-items: center;
          height: 150px;
          color: #ef6a2e;
          font-weight: 700;
          background: linear-gradient(160deg, rgba(239,106,46,0.08), rgba(255,255,255,0.96));
        }
        .share-footer {
          padding: 18px 22px 22px;
          border-top: 1px dashed rgba(71,58,52,0.14);
          color: #8a746a;
          font-size: 13px;
          text-align: center;
        }
        @media (max-width: 760px) {
          .share-grid,
          .share-metrics,
          .share-two-col,
          .share-media-grid { grid-template-columns: 1fr; }
          .share-hero, .share-body { padding: 18px; }
        }
      </style>
    </head>
    <body>
      <main class="share-page">
        <section class="share-sheet">
          <header class="share-hero">
            <div class="share-brand">
              <img src="${brandLogoUrl}" alt="神兽体育" />
              <div class="share-brand-text">
                <strong>神兽体育</strong>
                <span>MYTHICAL CREATURES SPORTS</span>
              </div>
            </div>
            <h1>${escapeHtml(report.athlete.name)} 青少年训练课后成长汇报</h1>
            <p>${escapeHtml(report.parent_friendly.headline)}</p>
            <div class="share-tags">
              ${(report.parent_friendly.tags || []).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}
            </div>
          </header>
          <section class="share-body">
            <div class="share-grid">
              <article class="share-card share-mini"><span>学员</span><strong>${escapeHtml(report.athlete.name)}</strong></article>
              <article class="share-card share-mini"><span>年龄</span><strong>${escapeHtml(String(report.athlete.age || ""))} 岁</strong></article>
              <article class="share-card share-mini"><span>课程日期</span><strong>${escapeHtml(report.session.date || "")}</strong></article>
              <article class="share-card share-mini"><span>课堂投入</span><strong>${escapeHtml(report.session.engagement || "")}</strong></article>
            </div>

            <article class="share-card">
              <h2>本次课程概览</h2>
              <p>${escapeHtml(report.parent_friendly.intro || "")}</p>
              <div class="share-callout">${escapeHtml(report.parent_friendly.progress_summary || "")}</div>
            </article>

            <div class="share-metrics">
              <article class="share-card share-score">
                <span>综合进展</span>
                <strong>${escapeHtml(String(progressChart.overall_score || 0))}</strong>
                <small>本周与上周对比 ${progressChart.weekly_delta >= 0 ? "+" : ""}${escapeHtml(String(progressChart.weekly_delta || 0))} 分</small>
              </article>
              <article class="share-card">
                <h3>各维度进展</h3>
                <div class="share-progress-list">${dimensionHtml}</div>
              </article>
            </div>

            <div class="share-two-col">
              <article class="share-card share-ring-wrap">
                <h3>周期目标完成度</h3>
                ${buildGoalRingSvg(progressChart.goal_completion || 0)}
              </article>
              <article class="share-card share-trend">
                <h3>最近训练趋势</h3>
                ${buildTrendSvg(progressChart.trend || [])}
              </article>
            </div>

            <div class="share-two-col">
              <article class="share-card">
                <h3>本周主线进展</h3>
                <p>${escapeHtml(report.parent_friendly.current_track_progress || "")}</p>
                <p>${escapeHtml(report.parent_friendly.coach_observation || "")}</p>
              </article>
              <article class="share-card">
                <h3>下节课衔接建议</h3>
                <p>${escapeHtml(report.parent_friendly.next_session_bridge || "")}</p>
                <div class="share-callout">家庭配合建议：${escapeHtml((report.parent_friendly.parent_actions || [])[1] || "保持规律作息、补水和轻量家庭练习。")}</div>
              </article>
            </div>

            <article class="share-card">
              <h3>家长配合建议</h3>
              <ul class="share-list">
                ${(report.parent_friendly.parent_actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
              </ul>
            </article>

            <article class="share-card">
              <h3>训练素材</h3>
              <div class="share-media-grid">
                ${mediaHtml || `<div class="share-callout">本次未上传训练照片或短视频，可在下一次训练后补充更完整的课堂素材。</div>`}
              </div>
            </article>
          </section>
          <footer class="share-footer">神兽体育青少年体适能训练会员课件系统与报告平台</footer>
        </section>
      </main>
    </body>
  </html>`;
}

function openParentShareWindow(report, options = {}) {
  if (!report) return;
  const autoPrint = Boolean(options.autoPrint);
  let html = buildParentShareHtml(report);
  if (autoPrint) {
    html = html.replace(
      "</body>",
      `<script>window.addEventListener("load",()=>setTimeout(()=>window.print(),320));</script></body>`,
    );
  }
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const shareUrl = URL.createObjectURL(blob);
  const shareWindow = window.open(shareUrl, "_blank", "width=980,height=1200");
  if (!shareWindow) {
    setStatus("浏览器拦截了长图窗口，请允许弹窗后重试", "error");
    return;
  }
  shareWindow.focus();
  setTimeout(() => URL.revokeObjectURL(shareUrl), 3000);
}

function openParentReportPdfWindow(report) {
  openParentShareWindow(report, { autoPrint: true });
}

function renderParentReportPreview(report) {
  if (!report) {
    parentReportPreview.innerHTML = `<div class="empty-state">保存一次训练报告后，这里会生成更适合发给家长的图文版汇报。</div>`;
    return;
  }
  currentReport = report;

  const mediaHtml = (report.media || [])
    .map((item) => {
      if (item.kind === "video") {
        return `
          <figure class="media-card">
            <video controls preload="metadata" src="${item.url}"></video>
            <figcaption>${item.name}</figcaption>
          </figure>
        `;
      }
      return `
        <figure class="media-card">
          <img src="${item.url}" alt="${item.name}" loading="lazy" />
          <figcaption>${item.name}</figcaption>
        </figure>
      `;
    })
    .join("");

  const progressChart = report.parent_friendly.progress_chart || { dimensions: [], trend: [], overall_score: 0 };
  const weeklyDelta = progressChart.weekly_delta || 0;
  const dimensionHtml = progressChart.dimensions
    .map(
      (item) => `
        <div class="progress-bar-card">
          <div class="progress-bar-top">
            <strong>${item.label}</strong>
            <span>${item.score} 分 · ${item.delta >= 0 ? "+" : ""}${item.delta}</span>
          </div>
          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width: ${item.score}%;"></div>
          </div>
          <small>${item.status}</small>
        </div>
      `,
    )
    .join("");

  parentReportPreview.innerHTML = `
    <article class="parent-report-card">
      <div class="parent-report-top">
        <div>
          <span class="report-badge">${report.athlete.name} 课后汇报</span>
          <strong>${report.parent_friendly.headline}</strong>
          <p>${report.parent_friendly.intro}</p>
        </div>
        <div class="head-actions">
          <button id="refresh-parent-share-btn" class="ghost accent-ghost" type="button">重新生成长图</button>
          <button id="export-parent-pdf-btn" class="ghost" type="button">导出 PDF</button>
        </div>
      </div>
      <div class="tag-row">
        ${report.parent_friendly.tags.map((tag) => `<span>${tag}</span>`).join("")}
      </div>
      <section class="report-section">
        <h3>本阶段进展图表</h3>
        <p>${report.parent_friendly.progress_summary || ""}</p>
        <div class="progress-overview">
          <div class="progress-score-card">
            <span>综合进展</span>
            <strong>${progressChart.overall_score || 0}</strong>
            <small>基于近期课堂投入、动作规范、体能表现和训练习惯估算</small>
          </div>
          <div class="progress-dimension-grid">${dimensionHtml}</div>
        </div>
        <div class="progress-meta-grid">
          <div class="progress-trend-card goal-ring-card">
            <h4>周期目标完成度</h4>
            ${buildGoalRingSvg(progressChart.goal_completion || 0)}
          </div>
          <div class="progress-trend-card">
            <h4>本周 vs 上周</h4>
            <div class="comparison-row">
              <strong>${weeklyDelta >= 0 ? "+" : ""}${weeklyDelta} 分</strong>
              <span>${weeklyDelta >= 3 ? "相比上周有明显提升" : weeklyDelta >= 0 ? "相比上周保持稳定推进" : "本周需要进一步巩固"}</span>
            </div>
            <p>${report.parent_friendly.current_track_progress || ""}</p>
            <p>${report.parent_friendly.next_session_bridge || ""}</p>
          </div>
        </div>
        <div class="progress-trend-card">
          <h4>最近训练趋势</h4>
          ${buildTrendSvg(progressChart.trend || [])}
        </div>
      </section>
      <section class="report-section">
        <h3>教练观察</h3>
        <p>${report.parent_friendly.coach_observation}</p>
      </section>
      <section class="report-section">
        <h3>建议家长配合</h3>
        <div class="action-list">
          ${report.parent_friendly.parent_actions.map((item) => `<p>${item}</p>`).join("")}
        </div>
      </section>
      <section class="report-section">
        <h3>训练素材</h3>
        <div class="media-grid">${mediaHtml || `<div class="recent-empty">本次未上传训练照片或短视频。</div>`}</div>
      </section>
    </article>
  `;
}

async function loadBootstrap() {
  bootstrapData = await requestJson("/api/bootstrap");
  if (bootstrapData.auth) {
    applyAuthState(bootstrapData.auth);
  }
  renderOptions(trainingGoalEl, bootstrapData.goals);
  renderOptions(traineeGroupEl, bootstrapData.trainee_groups);
  renderOptions(cycleWeeksEl, bootstrapData.cycles, (value) => `${value} 周`);
  renderOptions(sessionsPerWeekEl, bootstrapData.frequencies, (value) => `${value} 次`);
  renderOptions(trainingTypeEl, bootstrapData.training_types);
  renderOptions(sessionDurationEl, bootstrapData.durations, (value) => `${value} 分钟`);
  renderOptions(reportDurationEl, bootstrapData.durations, (value) => `${value} 分钟`);
  renderAthleteList(bootstrapData.athlete_profiles || []);
  currentReportPage = 1;
  renderRecentReports(bootstrapData.recent_reports || []);
  sessionDateEl.value = new Date().toISOString().slice(0, 10);
  reportDurationEl.value = bootstrapData.durations[0];
  syncAgeBoundsByGroup();
}

async function fetchAuthStatus() {
  const auth = await requestJson("/api/auth-status");
  applyAuthState(auth);
  return auth;
}

async function handleLogin(event) {
  event.preventDefault();
  loginBtn.disabled = true;
  setAuthMessage("登录中，请稍候…", "idle");
  try {
    const response = await requestJson("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: loginUsernameEl.value.trim(),
        password: loginPasswordEl.value,
      }),
    });
    applyAuthState({ authenticated: true, user: response.user });
    await loadBootstrap();
    setStatus("已登录，系统数据已载入", "success");
  } catch (error) {
    setAuthMessage(error.message, "error");
  } finally {
    loginBtn.disabled = false;
  }
}

async function handleLogout() {
  logoutBtn.disabled = true;
  try {
    await requestJson("/api/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    bootstrapData = null;
    applyAuthState({ authenticated: false, user: null });
    setStatus("已退出登录", "idle");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    logoutBtn.disabled = false;
  }
}

async function refreshArchiveAndReports(response) {
  if (response.athlete_profiles) {
    bootstrapData.athlete_profiles = response.athlete_profiles;
    renderAthleteList(response.athlete_profiles);
  }
  if (response.recent_reports) {
    bootstrapData.recent_reports = response.recent_reports;
    renderRecentReports(response.recent_reports);
    if (currentReport?.id) {
      const refreshed = response.recent_reports.find((item) => item.id === currentReport.id)?.report;
      if (refreshed) {
        renderParentReportPreview(refreshed);
      }
    }
  }
}

async function handleSaveProfile() {
  saveProfileBtn.disabled = true;
  try {
    const response = await requestJson("/api/save-athlete-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(athletePayload()),
    });
    currentAthleteId = response.profile.id;
    await refreshArchiveAndReports(response);
    setStatus("档案已保存", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    saveProfileBtn.disabled = false;
  }
}

async function handleGeneratePlan(event) {
  event.preventDefault();
  generateBtn.disabled = true;
  setStatus("生成中", "loading");
  try {
    currentPlan = await requestJson("/api/generate-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(athletePayload()),
    });
    currentAthleteId = currentPlan.athlete.id || currentAthleteId;
    selectedLessonId = currentPlan.weekly_plan_detailed?.[0]?.sessions?.[0]?.id || "";
    emptyState.classList.add("hidden");
    planOutput.classList.remove("hidden");
    renderSummary(currentPlan);
    renderWeeklyPlan(currentPlan);
    const firstLesson = currentPlan.weekly_plan_detailed?.[0]?.sessions?.[0];
    renderLessonDetail(firstLesson);
    renderSessionTemplates(currentPlan);
    renderParentTemplate(currentPlan);
    coachNotesEl.value = "";
    applyLessonToReportDraft(firstLesson);
    setStatus("已生成课件", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    generateBtn.disabled = false;
  }
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ name: file.name, data_url: reader.result });
    reader.onerror = () => reject(new Error(`${file.name} 读取失败`));
    reader.readAsDataURL(file);
  });
}

async function handleSaveReport(event) {
  event.preventDefault();
  if (!currentPlan) {
    setStatus("请先生成训练计划", "error");
    return;
  }

  saveReportBtn.disabled = true;
  saveMessage.classList.add("hidden");
  try {
    const files = Array.from(mediaFilesEl.files || []);
    const media = await Promise.all(files.map(fileToDataUrl));
    const response = await requestJson("/api/save-session-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        athlete: currentPlan.athlete,
        plan: currentPlan,
        session: {
          date: sessionDateEl.value,
          duration: `${reportDurationEl.value}分钟`,
          engagement: engagementEl.value,
          rpe: rpeEl.value,
          content: sessionContentEl.value.trim(),
          coach_notes: coachNotesEl.value.trim(),
          homework: homeworkEl.value.trim(),
        },
        media,
      }),
    });
    saveMessage.textContent = `${response.message}，已归档 ${response.report.media.length} 个训练素材。`;
    saveMessage.classList.remove("hidden");
    renderParentReportPreview(response.report);
    await refreshArchiveAndReports(response);
    mediaFilesEl.value = "";
    setStatus("报告已保存", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    saveReportBtn.disabled = false;
  }
}

async function handleDeleteAthlete(athleteId) {
  const item = (bootstrapData?.athlete_profiles || []).find((entry) => entry.id === athleteId);
  const athleteName = item?.name || "该学员";
  if (!window.confirm(`确认删除“${athleteName}”档案吗？关联训练报告和媒体也会一起删除。`)) return;

  try {
    const response = await requestJson("/api/delete-athlete-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: athleteId }),
    });
    await refreshArchiveAndReports(response);
    if (currentAthleteId === athleteId) {
      currentAthleteId = "";
      currentPlan = null;
      currentReport = null;
      selectedLessonId = "";
      emptyState.classList.remove("hidden");
      planOutput.classList.add("hidden");
      renderLessonDetail(null);
      renderParentReportPreview(null);
      startNewAthlete();
    }
    setStatus(response.message || "学员档案已删除", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleDeleteReport(reportId) {
  const item = (bootstrapData?.recent_reports || []).find((entry) => entry.id === reportId);
  const athleteName = item?.athlete_name || "该学员";
  if (!window.confirm(`确认删除“${athleteName}”的这份训练报告吗？关联媒体也会一起删除。`)) return;

  try {
    const response = await requestJson("/api/delete-session-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: reportId }),
    });
    await refreshArchiveAndReports(response);
    if (currentReport?.id === reportId) {
      currentReport = null;
      renderParentReportPreview(null);
    }
    setStatus(response.message || "训练报告已删除", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

athleteList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-athlete-id]");
  if (deleteButton) {
    handleDeleteAthlete(deleteButton.dataset.deleteAthleteId);
    return;
  }

  const button = event.target.closest(".select-athlete");
  if (!button) return;
  const profile = (bootstrapData.athlete_profiles || []).find((item) => item.id === button.dataset.id)?.profile;
  if (!profile) return;
  applyProfile(profile);
  renderAthleteList(bootstrapData.athlete_profiles || []);
  setStatus(`已载入 ${profile.name} 档案`, "success");
});

recentReports.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-report-id]");
  if (deleteButton) {
    handleDeleteReport(deleteButton.dataset.deleteReportId);
    return;
  }
  const card = event.target.closest("[data-report-id]");
  if (!card) return;
  const selected = (bootstrapData?.recent_reports || []).find((item) => item.id === card.dataset.reportId);
  if (selected?.report) {
    renderParentReportPreview(selected.report);
    renderRecentReports(bootstrapData.recent_reports || []);
    setStatus(`已载入 ${selected.athlete_name} 的训练汇报`, "success");
  }
});

athleteSearchEl?.addEventListener("input", () => {
  renderAthleteList(bootstrapData?.athlete_profiles || []);
});

reportSearchEl?.addEventListener("input", () => {
  currentReportPage = 1;
  renderRecentReports(bootstrapData?.recent_reports || []);
});

reportFilterEl?.addEventListener("change", () => {
  currentReportPage = 1;
  renderRecentReports(bootstrapData?.recent_reports || []);
});

reportPaginationEl?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-report-page]");
  if (!button) return;
  currentReportPage = Number(button.dataset.reportPage || 1);
  renderRecentReports(bootstrapData?.recent_reports || []);
});

weeklyPlan.addEventListener("click", (event) => {
  const button = event.target.closest(".lesson-trigger");
  if (!button || !currentPlan) return;
  selectedLessonId = button.dataset.lessonId;
  const lesson = currentPlan.weekly_plan_detailed
    ?.flatMap((week) => week.sessions)
    .find((item) => item.id === selectedLessonId);
  renderWeeklyPlan(currentPlan);
  renderLessonDetail(lesson);
  applyLessonToReportDraft(lesson);
  setStatus(`已带入 ${lesson?.title || "当前课次"} 的训练内容`, "success");
});

document.addEventListener("click", (event) => {
  if (event.target.id === "print-lesson-btn") {
    const lesson = currentPlan?.weekly_plan_detailed
      ?.flatMap((week) => week.sessions)
      .find((item) => item.id === selectedLessonId);
    openPrintWindowForLesson(lesson);
  }
  if (event.target.id === "open-parent-share-btn") {
    openParentShareWindow(currentReport);
  }
  if (event.target.id === "refresh-parent-share-btn") {
    openParentShareWindow(currentReport);
  }
  if (event.target.id === "export-parent-pdf-btn") {
    openParentReportPdfWindow(currentReport);
  }
});

sampleBtn.addEventListener("click", fillSample);
newAthleteBtn?.addEventListener("click", startNewAthlete);
saveProfileBtn.addEventListener("click", handleSaveProfile);
planForm.addEventListener("submit", handleGeneratePlan);
reportForm.addEventListener("submit", handleSaveReport);
loginForm?.addEventListener("submit", handleLogin);
logoutBtn?.addEventListener("click", handleLogout);
sessionDurationEl.addEventListener("change", () => {
  reportDurationEl.value = sessionDurationEl.value;
});
traineeGroupEl.addEventListener("change", syncAgeBoundsByGroup);

async function initializeApp() {
  try {
    const auth = await fetchAuthStatus();
    if (auth.authenticated) {
      await loadBootstrap();
      setStatus("已登录，等待生成", "idle");
    } else {
      setAuthMessage("请输入教练账号和密码后进入系统。", "idle");
      setStatus("请先登录", "idle");
    }
  } catch (error) {
    setStatus(error.message, "error");
  }
}

initializeApp();
