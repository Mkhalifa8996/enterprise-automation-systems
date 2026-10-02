import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth, onAuthStateChanged, signInWithEmailAndPassword, signOut,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getDatabase, onValue, ref } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-database.js";

// تحميل إعدادات Firebase من ملف التكوين
// يجب إنشاء ملف firebase-config.js بإعدادات Firebase الخاصة بك
let firebaseConfig;
try {
  // محاولة استيراد الإعدادات من ملف التكوين المحلي
  const configModule = await import('./firebase-config.js');
  firebaseConfig = configModule.default;
} catch (e) {
  // إذا لم يتم العثور على ملف التكوين، استخدام إعدادات افتراضية للتطوير فقط
  console.warn('لم يتم العثور على ملف firebase-config.js - استخدام إعدادات التطوير');
  firebaseConfig = {
    apiKey: "",
    authDomain: "",
    databaseURL: "",
    projectId: "",
  };
}

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const database = getDatabase(app);
const $ = (id) => document.getElementById(id);

function text(value) {
  return String(value ?? "").trim();
}

function renderTrips(records) {
  const trips = records
    .filter((item) => item.sheet_key === "trips")
    .map((item) => item.data || {})
    .sort((a, b) => String(b.date || b.trip_date || "").localeCompare(String(a.date || a.trip_date || "")));
  $("trips-count").textContent = trips.length;
  $("trips-list").replaceChildren();
  if (!trips.length) {
    $("trips-list").innerHTML = '<p class="empty">لا توجد رحلات بعد.</p>';
    return;
  }
  trips.slice(0, 20).forEach((trip) => {
    const card = document.createElement("article");
    card.className = "trip-card";
    const title = text(trip.customer || trip.company || trip.description) || "رحلة";
    const route = [trip.from || trip.pickup_place, trip.to || trip.dropoff_place].filter(Boolean).join(" ← ");
    const heading = document.createElement("strong");
    heading.textContent = title;
    const routeText = document.createElement("span");
    routeText.textContent = route || "لا يوجد مسار مسجل";
    const meta = document.createElement("small");
    meta.textContent = `${text(trip.date || trip.trip_date)} · ${text(trip.car_no || trip.vehicle)}`;
    card.append(heading, routeText, meta);
    $("trips-list").append(card);
  });
}

function renderPartners(records) {
  const shares = records
    .filter((item) => item.sheet_key === "vehicle_partners")
    .map((item) => item.data || {});
  const payments = records
    .filter((item) => item.sheet_key === "partner_payments")
    .map((item) => item.data || {})
    .sort((a, b) => text(b.date).localeCompare(text(a.date)));
  $("partners-count").textContent = new Set(shares.map((s) => text(s.partner))).size;
  $("partner-payments-count").textContent = payments.length;

  $("partners-list").replaceChildren();
  if (!shares.length) {
    $("partners-list").innerHTML = '<p class="empty">لا توجد شراكات مسجلة بعد.</p>';
  } else {
    // نجمّع النسب حسب الشريك لعرض ملكيته من كل سيارة.
    const byPartner = new Map();
    shares.forEach((share) => {
      const name = text(share.partner);
      if (!name) return;
      const entry = byPartner.get(name) || { name, cars: [], total: 0, locked: false };
      const pct = Number(share.ownership_pct) || 0;
      entry.cars.push(`${text(share.car_no)} (${pct}%)`);
      entry.total += pct;
      entry.locked = entry.locked || text(share.locked) === "نعم";
      byPartner.set(name, entry);
    });
    [...byPartner.values()]
      .sort((a, b) => b.total - a.total)
      .forEach((entry) => {
        const card = document.createElement("article");
        card.className = "trip-card";
        const title = document.createElement("strong");
        title.textContent = entry.name;
        const cars = document.createElement("span");
        cars.textContent = entry.cars.join(" · ");
        const meta = document.createElement("small");
        meta.textContent = `إجمالي النسبة ${entry.total}%${entry.locked ? " · مثبّتة" : ""}`;
        card.append(title, cars, meta);
        $("partners-list").append(card);
      });
  }

  $("partner-payments-list").replaceChildren();
  if (!payments.length) {
    $("partner-payments-list").innerHTML = '<p class="empty">لا توجد دفعات مسجلة بعد.</p>';
  } else {
    payments.slice(0, 20).forEach((payment) => {
      const card = document.createElement("article");
      const voided = text(payment.voided) === "مشطوبة";
      card.className = voided ? "trip-card is-voided" : "trip-card";
      const title = document.createElement("strong");
      title.textContent = `${text(payment.payment_type)} — ${text(payment.partner)}`;
      const amount = document.createElement("span");
      amount.textContent = `${Number(payment.amount || 0).toFixed(3)} د.ك`;
      const meta = document.createElement("small");
      meta.textContent = [text(payment.date), text(payment.car_no), voided ? "مشطوبة" : ""]
        .filter(Boolean).join(" · ");
      card.append(title, amount, meta);
      $("partner-payments-list").append(card);
    });
  }
}

function renderDrivers(records) {
  const drivers = records
    .filter((item) => item.sheet_key === "drivers")
    .map((item) => item.data || {});
  $("drivers-count").textContent = drivers.length;
  $("external-drivers-count").textContent =
    drivers.filter((d) => text(d.driver_type) === "خارجي").length;

  $("drivers-list").replaceChildren();
  if (!drivers.length) {
    $("drivers-list").innerHTML = '<p class="empty">لا يوجد سائقون بعد.</p>';
    return;
  }
  drivers
    .slice()
    .sort((a, b) => text(a.name).localeCompare(text(b.name)))
    .forEach((driver) => {
      const card = document.createElement("article");
      const kind = text(driver.driver_type) || "غير محدد";
      card.className = kind === "خارجي" ? "trip-card is-external" : "trip-card";
      const title = document.createElement("strong");
      title.textContent = text(driver.name) || "سائق";
      const badge = document.createElement("span");
      badge.textContent = `نوع السائق: ${kind}`;
      const meta = document.createElement("small");
      meta.textContent = [text(driver.phone), text(driver.license_no)]
        .filter(Boolean).join(" · ") || "لا توجد بيانات تواصل";
      card.append(title, badge, meta);
      $("drivers-list").append(card);
    });
}

function renderData(payload) {
  const records = Array.isArray(payload?.records) ? payload.records : [];
  $("vehicles-count").textContent = records.filter((item) => item.sheet_key === "vehicles").length;
  $("invoices-count").textContent = records.filter((item) => item.sheet_key === "invoices").length;
  $("records-count").textContent = `${records.length} سجل`;
  renderTrips(records);
  renderPartners(records);
  renderDrivers(records);
  $("sync-status").textContent = "البيانات محدثة";
}

function listenToData() {
  $("sync-status").textContent = "جارٍ تحميل البيانات…";
  onValue(ref(database, "transport_sync"), (snapshot) => renderData(snapshot.val()), (error) => {
    $("sync-status").textContent = `تعذر تحميل البيانات: ${error.code}`;
  });
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.toggle("is-active", item === tab));
      // كل لوحة تُعرض حسب التبويب المختار.
      ["tab-trips", "tab-drivers", "tab-partners"].forEach((id) => {
        const panel = $(id);
        if (panel) panel.hidden = id !== tab.dataset.tab;
      });
    });
  });
}

setupTabs();

$("login-btn").addEventListener("click", async () => {
  $("login-error").textContent = "";
  $("login-btn").disabled = true;
  try {
    await signInWithEmailAndPassword(auth, $("email").value.trim(), $("password").value);
  } catch (error) {
    $("login-error").textContent = "تعذر تسجيل الدخول. تحقق من البريد وكلمة المرور.";
  } finally {
    $("login-btn").disabled = false;
  }
});

$("logout-btn").addEventListener("click", () => signOut(auth));
onAuthStateChanged(auth, (user) => {
  $("login-view").hidden = Boolean(user);
  $("dashboard-view").hidden = !user;
  if (user) listenToData();
});
