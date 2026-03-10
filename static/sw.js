self.addEventListener("push", function (event) {
    let data = { title: "Market Dashboard", body: "You have a new alert.", url: "/" };
    try {
        data = event.data.json();
    } catch (_) {}

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: "/static/images/stock_bg3.jpg",
            badge: "/static/images/stock_bg3.jpg",
            data: { url: data.url },
        })
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
            const url = event.notification.data.url || "/";
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && "focus" in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            if (clients.openWindow) return clients.openWindow(url);
        })
    );
});
