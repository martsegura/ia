/**
 * Cliente HTTP mínimo de SaluDuoc.
 * Todas las peticiones incluyen la cookie HttpOnly de sesión.
 */
const api = async (path, options = {}) => {
  const { headers, ...rest } = options;
  const response = await fetch(`/api/v1${path}`, {
    ...rest,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(headers || {}) },
  });

  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    /* respuesta sin cuerpo JSON */
  }

  if (!response.ok) {
    let detail = "Error inesperado";
    if (typeof data?.detail === "string") {
      detail = traducirError(data.detail);
    } else if (Array.isArray(data?.detail)) {
      detail = data.detail.map((item) => traducirError(item.msg || "Dato inválido")).join(". ");
    }

    if (response.status === 401 && !["/login", "/registro"].includes(window.location.pathname)) {
      window.location.href = "/login";
    }
    throw new Error(detail);
  }
  return data;
};

/** Traduce los mensajes de validación más comunes al español. */
const traducirError = (message) => {
  const limpio = String(message).replace(/^Value error,\s*/i, "");
  const reglas = [
    [/not a valid email address/i, "Ingresa un correo electrónico válido"],
    [/String should have at least (\d+) character/i, "El campo debe tener al menos $1 caracteres"],
    [/String should have at most (\d+) character/i, "El campo no puede superar los $1 caracteres"],
    [/Field required/i, "Este campo es obligatorio"],
    [/Input should be a valid/i, "El valor ingresado no es válido"],
  ];
  for (const [patron, reemplazo] of reglas) {
    if (patron.test(limpio)) return limpio.replace(patron, reemplazo);
  }
  return limpio;
};

const ROLE_HOME = {
  patient: "/paciente",
  doctor: "/medico",
  admin: "/admin",
};

window.SaluDuoc = { api };

document.addEventListener("DOMContentLoaded", () => {
  const message = document.getElementById("message");

  const showMessage = (text, type = "error") => {
    if (!message) return;
    message.textContent = text;
    message.className = `message ${type}`;
  };

  const logoutButton = document.getElementById("logout-btn");
  if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
      try {
        await api("/auth/logout", { method: "POST" });
      } finally {
        window.location.href = "/login";
      }
    });
  }

  // Rellenar credenciales demo (solo visible en dev/test).
  document.querySelectorAll(".demo-fill").forEach((button) => {
    button.addEventListener("click", () => {
      document.getElementById("email").value = button.dataset.email;
      document.getElementById("password").value = "Demo123!";
      showMessage("Credenciales demo cargadas. Presiona Entrar.", "ok");
    });
  });

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      showMessage("");
      const submit = loginForm.querySelector("button[type=submit]");
      submit.disabled = true;
      try {
        const user = await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: document.getElementById("email").value.trim(),
            password: document.getElementById("password").value,
          }),
        });
        showMessage(`Bienvenido, ${user.full_name}`, "ok");
        window.location.href = ROLE_HOME[user.role] || "/";
      } catch (error) {
        showMessage(error.message);
      } finally {
        submit.disabled = false;
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      showMessage("");
      const submit = registerForm.querySelector("button[type=submit]");
      submit.disabled = true;
      try {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            full_name: document.getElementById("full_name").value.trim(),
            email: document.getElementById("email").value.trim(),
            password: document.getElementById("password").value,
          }),
        });
        showMessage("Cuenta creada. Entrando a tu sesión...", "ok");
        // El registro deja la cookie de sesión: vamos directo al panel.
        setTimeout(() => (window.location.href = "/paciente"), 700);
      } catch (error) {
        showMessage(error.message);
      } finally {
        submit.disabled = false;
      }
    });
  }
});

/* --- Formularios de signos vitales --- */
const numberOrNull = (id) => {
  const element = document.getElementById(id);
  if (!element || element.value === "") return null;
  const value = Number(element.value);
  return Number.isFinite(value) ? value : null;
};

const checkedSymptoms = () =>
  Array.from(document.querySelectorAll('input[name="symptoms"]:checked')).map(
    (input) => input.value
  );

document.addEventListener("DOMContentLoaded", () => {
  const message = document.getElementById("message");
  const showMessage = (element, text, type = "error") => {
    if (!element) return;
    element.textContent = text;
    element.className = `message ${type}`;
    if (!text) element.className = "message";
  };

  // Pestañas de registro
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      tab.classList.add("active");
      const panel = document.getElementById(`tab-${tab.dataset.tab}`);
      if (panel) panel.classList.add("active");
    });
  });

  // Dolor
  const pain = document.getElementById("pain_scale");
  const painOutput = document.getElementById("pain-output");
  if (pain && painOutput) {
    pain.addEventListener("input", () => (painOutput.textContent = pain.value));
  }

  // "Ninguno" excluye al resto de síntomas
  const symptomBoxes = Array.from(document.querySelectorAll('input[name="symptoms"]'));
  symptomBoxes.forEach((box) => {
    box.addEventListener("change", () => {
      if (!box.checked) return;
      if (box.value === "Ninguno") {
        symptomBoxes.forEach((other) => {
          if (other !== box) other.checked = false;
        });
      } else {
        const none = symptomBoxes.find((other) => other.value === "Ninguno");
        if (none) none.checked = false;
      }
    });
  });

  const vitalsForm = document.getElementById("vitals-form");
  if (vitalsForm) {
    vitalsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const target = document.getElementById("vitals-message");
      showMessage(target, "");
      const payload = {
        recorded_at: document.getElementById("recorded_at").value
          ? new Date(document.getElementById("recorded_at").value).toISOString()
          : null,
        heart_rate_bpm: numberOrNull("heart_rate_bpm"),
        systolic_mmhg: numberOrNull("systolic_mmhg"),
        diastolic_mmhg: numberOrNull("diastolic_mmhg"),
        spo2_pct: numberOrNull("spo2_pct"),
        sleep_quality_score: numberOrNull("sleep_quality_score"),
        sleep_hours: numberOrNull("sleep_hours"),
        pain_scale: numberOrNull("pain_scale"),
        symptoms: checkedSymptoms(),
        onset: document.getElementById("onset").value || null,
        notes: document.getElementById("notes").value.trim() || null,
        establishment_id: document.getElementById("queue-establishment").value || null,
      };
      if (
        payload.heart_rate_bpm === null &&
        payload.systolic_mmhg === null &&
        payload.diastolic_mmhg === null &&
        payload.spo2_pct === null
      ) {
        showMessage(target, "Ingresa al menos un signo vital (FC, presión o saturación).");
        return;
      }
      const submit = vitalsForm.querySelector("button[type=submit]");
      submit.disabled = true;
      try {
        await api("/vitals", { method: "POST", body: JSON.stringify(payload) });
        showMessage(target, "Registro enviado. Calculando categoría...", "ok");
        window.location.assign("/paciente?registro=1#resultado");
      } catch (error) {
        showMessage(target, error.message);
      } finally {
        submit.disabled = false;
      }
    });
  }

  const uploadForm = document.getElementById("upload-form");
  if (uploadForm) {
    const fileInput = document.getElementById("watch-file");
    const textarea = document.getElementById("watch-json");
    if (fileInput) {
      fileInput.addEventListener("change", async () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        textarea.value = await file.text();
        showMessage(document.getElementById("upload-message"), `Archivo ${file.name} cargado.`, "ok");
      });
    }

    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const target = document.getElementById("upload-message");
      showMessage(target, "");
      let data;
      try {
        data = JSON.parse(textarea.value);
      } catch (_) {
        showMessage(target, "El contenido no es un JSON válido.");
        return;
      }
      if (!data.records && (data.heart_rate_bpm || data.blood_pressure || data.oxygen_saturation_pct)) {
        data = { device: data.device || "Reloj inteligente", records: [data] };
      }
      if (!Array.isArray(data.records) || data.records.length === 0) {
        showMessage(target, "El JSON debe incluir una lista 'records' con al menos un registro.");
        return;
      }
      data.establishment_id = document.getElementById("queue-establishment").value || null;
      const submit = uploadForm.querySelector("button[type=submit]");
      submit.disabled = true;
      try {
        await api("/vitals/upload", { method: "POST", body: JSON.stringify(data) });
        showMessage(target, "JSON procesado. Calculando categoría...", "ok");
        window.location.assign("/paciente?registro=1#resultado");
      } catch (error) {
        showMessage(target, error.message);
      } finally {
        submit.disabled = false;
      }
    });
  }

  // Acciones de la cola médica
  document.querySelectorAll("[data-queue-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const status = button.dataset.queueAction;
      const entryId = button.dataset.entry;
      if (status === "left" && !window.confirm("¿Retirar a este paciente de la cola?")) return;
      button.disabled = true;
      try {
        await api(`/queue/${entryId}/status`, {
          method: "POST",
          body: JSON.stringify({ status }),
        });
        window.location.reload();
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
      }
    });
  });

  const refreshQueue = document.getElementById("refresh-queue");
  if (refreshQueue) {
    refreshQueue.addEventListener("click", () => window.location.reload());
  }
});
