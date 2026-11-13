"use strict";

const form = document.getElementById("review-form");
const username = document.getElementById("username");
const jobInput = document.getElementById("job-input");
const status = document.getElementById("form-status");

function validationMessage(input) {
  const value = input.value.trim();
  if (input === username) {
    if (!value) return "Enter your GitHub username.";
    if (value.length > 39 || !/^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$/.test(value)) {
      return "Use a GitHub username of up to 39 letters, numbers, or single hyphens between words. Leave out the profile URL.";
    }
  } else {
    if (!value) return "Enter a job title or job description.";
    if (value.length > 3000) return "Keep the job description within 3000 characters.";
  }
  return "";
}

function showValidation(input) {
  const message = validationMessage(input);
  const error = document.getElementById(input === username ? "username-error" : "job-error");
  error.textContent = message;
  error.hidden = !message;
  input.setAttribute("aria-invalid", String(Boolean(message)));
  return !message;
}

for (const input of [username, jobInput]) {
  input.addEventListener("blur", () => showValidation(input));
  input.addEventListener("input", () => {
    status.textContent = "";
    if (input.getAttribute("aria-invalid") === "true") showValidation(input);
  });
}

jobInput.addEventListener("input", () => {
  document.getElementById("job-count").textContent = `${jobInput.value.length} / 3000`;
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  status.textContent = "";
  username.value = username.value.trim();
  jobInput.value = jobInput.value.trim();
  document.getElementById("job-count").textContent = `${jobInput.value.length} / 3000`;
  const usernameValid = showValidation(username);
  const jobValid = showValidation(jobInput);
  if (!usernameValid || !jobValid) {
    (usernameValid ? jobInput : username).focus();
    return;
  }
  // Step 1 validates the form locally; API submission is the next phase step.
  status.textContent = "Your details are ready. Review generation is coming soon.";
});
