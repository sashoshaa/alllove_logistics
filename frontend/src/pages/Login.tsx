import React from "react";
import { useLogin } from "@refinedev/core";
import { Alert, Button, Form, Input } from "antd";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export const Login: React.FC = () => {
  const { mutate: login, isPending, data } = useLogin<{ email: string; password: string }>();
  const errorMessage = data && !data.success ? data.error?.message : undefined;
  const [installEvent, setInstallEvent] = React.useState<BeforeInstallPromptEvent>();
  const [installed, setInstalled] = React.useState(
    () => window.matchMedia("(display-mode: standalone)").matches,
  );

  React.useEffect(() => {
    const onPrompt = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setInstallEvent(undefined);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const installApp = async () => {
    if (!installEvent) return;
    await installEvent.prompt();
    setInstallEvent(undefined);
  };

  return (
    <div className="login-screen">
      <section className="login-hero">
        <div>
          <p style={{ letterSpacing: "0.22em", textTransform: "uppercase", fontSize: 12, color: "#c4a574" }}>
            шоурум одежды
          </p>
          <h1>AllLove</h1>
          <p>Веб для сотрудников шоурума. Проверка поставок — в этом же приложении на телефоне или в десктоп-клиенте валидатора.</p>
        </div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <p className="login-title">Вход в логистику</p>
          <p className="login-note">Рабочее место открывается по роли: шоурум, проверка или администрирование.</p>
          {errorMessage && <Alert type="error" message={errorMessage} style={{ marginBottom: 16 }} />}
          <Form layout="vertical" onFinish={(values) => login(values)}>
            <Form.Item label="Email" name="email" rules={[{ required: true, message: "Введите email" }]}>
              <Input size="large" placeholder="email@alllove.ru" autoComplete="username" />
            </Form.Item>
            <Form.Item label="Пароль" name="password" rules={[{ required: true, message: "Введите пароль" }]}>
              <Input.Password size="large" autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={isPending} block size="large">
              Войти
            </Button>
          </Form>
          {!installed && (
            <div className="install-hint">
              {installEvent ? (
                <Button onClick={() => void installApp()} block>
                  Установить на телефон или рабочий стол
                </Button>
              ) : (
                <p>
                  На телефоне: меню браузера → «На экран Домой». На компьютере валидатора также есть отдельное
                  приложение: <code>python -m desktop</code>
                </p>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
