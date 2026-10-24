/**
 * Cliente HTTP mínimo de SaluDuoc.
 * Todas las peticiones incluyen la cookie HttpOnly de sesión.
 */
const api = async (path, options = {}) => {
  const response = await fetch(`/api/v1${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    /* respuesta sin cuerpo JSON */
  }

  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "Error inesperado";
    throw new Error(detail);
  }
  return data;
};

window.SaluDuoc = { api };

document.addEventListener("DOMContentLoaded", () => {
  const message = document.getElementById("message");

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
