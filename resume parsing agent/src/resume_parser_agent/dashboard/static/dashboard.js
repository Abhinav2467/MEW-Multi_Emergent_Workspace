const events = new EventSource("/events");

events.addEventListener("message", (event) => {
  const payload = JSON.parse(event.data);
  if (payload.type === "resume_saved" || payload.type === "resume_deleted") {
    window.location.reload();
  }
});
