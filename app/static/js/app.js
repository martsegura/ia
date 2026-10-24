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
