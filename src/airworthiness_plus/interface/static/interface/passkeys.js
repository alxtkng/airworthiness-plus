"use strict";

(() => {
    if (!window.PublicKeyCredential || !navigator.credentials) return;

    function decode(value) {
        return Uint8Array.from(atob(value.replaceAll("-", "+").replaceAll("_", "/")),
            character => character.charCodeAt(0));
    }

    function encode(value) {
        if (!value) return null;
        const bytes = new Uint8Array(value);
        let binary = "";
        for (const byte of bytes) binary += String.fromCharCode(byte);
        return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
    }

    function prepare(options) {
        options.challenge = decode(options.challenge);
        if (options.user) options.user.id = decode(options.user.id);
        for (const key of ["allowCredentials", "excludeCredentials"]) {
            if (options[key]) {
                for (const credential of options[key]) credential.id = decode(credential.id);
            }
        }
        return options;
    }

    function serialise(credential) {
        const response = credential.response;
        const data = {clientDataJSON: encode(response.clientDataJSON)};
        if (response.attestationObject) {
            data.attestationObject = encode(response.attestationObject);
            if (response.getTransports) data.transports = response.getTransports();
        } else {
            data.authenticatorData = encode(response.authenticatorData);
            data.signature = encode(response.signature);
            data.userHandle = encode(response.userHandle);
        }
        return {id: credential.id, rawId: encode(credential.rawId), type: credential.type, response: data};
    }

    async function send(button, form, data) {
        const response = await fetch(button.dataset.url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": form.elements.namedItem("csrfmiddlewaretoken").value,
            },
            body: JSON.stringify(data),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Start again to use a passkey.");
        return result;
    }

    for (const button of document.querySelectorAll("[data-passkey]")) {
        button.hidden = false;
        button.addEventListener("click", async () => {
            const form = button.form;
            const kind = button.dataset.passkey;
            const name = form.elements.namedItem(kind === "register" ? "name" : "username");
            const message = form.querySelector("[data-passkey-message]");
            if (name && !name.reportValidity()) return;
            if (message) message.hidden = true;
            button.disabled = true;
            try {
                const input = kind === "sign-in" ? {username: name.value} : {};
                const {ceremony, publicKey} = await send(button, form, input);
                if (!ceremony) throw new Error("Refresh the page to continue.");
                const options = {publicKey: prepare(publicKey)};
                const credential = await (kind === "register"
                    ? navigator.credentials.create(options)
                    : navigator.credentials.get(options));
                const body = {ceremony, credential: serialise(credential)};
                if (kind === "register") body.name = name.value;
                const result = await send(button, form, body);
                if (result.redirect) {
                    window.location.assign(result.redirect);
                } else if (result.verified === true) {
                    if (kind === "verify-submit") HTMLFormElement.prototype.submit.call(form);
                    else window.location.reload();
                }
            } catch (error) {
                if (message) {
                    message.textContent = error instanceof DOMException
                        ? "Passkey Was Not Used. Try Again or Use Your Authenticator App."
                        : error instanceof SyntaxError
                            ? "Refresh the Page and Try Again."
                            : error.message;
                    message.hidden = false;
                }
            } finally {
                button.disabled = false;
            }
        });
    }
})();
