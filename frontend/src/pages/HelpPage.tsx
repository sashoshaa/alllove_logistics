import React from "react";
import { Card, Col, Row } from "antd";

export const HelpPage: React.FC = () => (
  <>
    <h1 className="page-title">Справка</h1>
    <p className="page-lead">Краткие сценарии трёх ролей. Полный текст — в docs/guides.md.</p>
    <Row gutter={[16, 16]}>
      <Col xs={24} md={8}>
        <Card className="help-card">
          <h3>Администратор</h3>
          <p>Заводит людей и справочники, смотрит журнал и историю поставки, делает копии. Не сверяет товар и не принимает предложения по поставке.</p>
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card className="help-card">
          <h3>Шоурум</h3>
          <p>Собирает поставку из номенклатуры, прикладывает PDF/JPG/PNG, назначает одного ответственного. Просрочка — признак рядом со статусом.</p>
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card className="help-card">
          <h3>Валидатор</h3>
          <p>Очередь «На проверке» в вебе, на телефоне (установка на Домой) или в десктоп-приложении <code>python -m desktop</code>. Факт по каждой позиции обязателен.</p>
        </Card>
      </Col>
    </Row>
  </>
);
