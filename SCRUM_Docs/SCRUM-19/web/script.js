const emailForm = document.getElementById("emailForm");
const status = document.getElementById("status");

emailForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const to = document.getElementById("to").value;
    const subject = document.getElementById("subject").value;
    const body = document.getElementById("body").value;
    const attachment = document.getElementById("attachment").files[0];

    console.log("To:", to);
    console.log("Subject:", subject);
    console.log("Body:", body);
    console.log("Attachment:", attachment);

    status.textContent = "Email form submitted successfully.";
});