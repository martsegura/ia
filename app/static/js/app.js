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
      detail = data.detail;
    } else if (Array.isArray(data?.detail)) {
      detail = data.detail.map((item) => item.msg || "Dato inválido").join(". ");
    }

    if (response.status === 401 && !["/login", "/registro"].includes(window.location.pathname)) {
      window.location.href = "/login";
    }
    throw new Error(detail);
  }
  return data;
};

window.SaluDuoc = { api };

document.addEventListener("DOMContentLoaded", async () => {
  const message = document.getElementById("message");

  // Navegación según sesión: muestra "Cerrar sesión" cuando hay usuario.
  const nav = document.querySelector(".nav");
  if (nav && !["/login", "/registro"].includes(window.location.pathname)) {
    try {
      const user = await api("/auth/me");
      const label = document.createElement("span");
      label.className = "muted";
      label.textContent = user.full_name;
      const logout = document.createElement("button");
      logout.type = "button";
      logout.className = "btn btn-sm";
      logout.textContent = "Cerrar sesión";
      logout.addEventListener("click", async () => {
        try {
          await api("/auth/logout", { method: "POST" });
        } finally {
          window.location.href = "/login";
        }
      });
      nav.replaceChildren(label, logout);
    } catch (_) {
      /* visitante */
    }
  }

  const showMessage = (text, type = "error") => {
    if (!message) return;
    message.textContent = text;
    message.className = `message ${type}`;
  };

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
        window.location.href = "/";
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
        showMessage("Cuenta creada. Ahora puedes iniciar sesión.", "ok");
        setTimeout(() => (window.location.href = "/login"), 900);
      } catch (error) {
        showMessage(error.message);
      } finally {
        submit.disabled = false;
      }
    });
  }
});
