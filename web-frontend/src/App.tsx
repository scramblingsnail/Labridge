import { useState } from "react";
import "./App.css";
import axios from "axios";
import { useInterval } from "ahooks";
import Markdown from "react-markdown";

import {
  Input,
  Spin,
  Button,
  message,
  Modal,
  Form,
  Checkbox,
  Tooltip,
  Flex,
} from "antd";

import {
  SettingOutlined,
  FilePdfFilled,
  LockOutlined,
  UserOutlined,
} from "@ant-design/icons";

const styles = {
  lightBackground: "#FFFFFF",
  middleBackground: "#F6F7F7",
  middleDarkBackground: "#b5b6b6",
  darkBackground: "#EFEFEF",
  darkDarkBackground: "#595757",
  systemTextBackground: "#FFFFFF",
  userTextBackground: "#b7deca",
  fontSize: "18px",
};

function App() {
  // const [serverAddress, setServerAddress] = useState("localhost:6006");
  const [serverAddress, setServerAddress] = useState("210.28.141.187");
  const baseurl = "http://" + serverAddress;
  const [userID, setUserID] = useState("realzhao");
  const [userInput, setUserInput] = useState("");
  const [inOneChatRound, setInOneChatRound] = useState(false);
  const [showSignupModal, setShowSignupModal] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const defaultUserSettings = {
    reply_in_speech: false,
    enable_instruct: false,
    enable_comment: false,
  };
  const [userSettings, setUserSettings] = useState<typeof defaultUserSettings>(
    JSON.parse(
      localStorage.getItem("userSettings") ||
        JSON.stringify(defaultUserSettings)
    )
  );
  localStorage.setItem("userSettings", JSON.stringify(userSettings));
  const [chatMessages, setChatMessages] = useState<
    {
      role: "user" | "system";
      content: string;
      extraInfo?: string | null;
      files?: string[];
    }[]
  >([]);
  const [isInnerChat, setIsInnerChat] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPDFURL, setShowPDFURL] = useState<null | string>(null);

  useInterval(async () => {
    const r = await axios.get(baseurl + `/users/${userID}/response`);

    const data: {
      reply_text: string;
      valid: boolean;
      references: null | Record<string, number>;
      extra_info: null;
      error: null;
      inner_chat: boolean;
    } = r.data;
    if (data.valid === true) {
      setChatMessages((old) => [
        ...old,
        {
          role: "system",
          content: data.reply_text,
          extraInfo: data.extra_info,
          files: (data.references && Object.keys(data.references)) || undefined,
        },
      ]);
      setIsInnerChat(data.inner_chat);
    }
  }, 1000);

  const sendUserInput = async () => {
    setInOneChatRound(true);
    setChatMessages([...chatMessages, { role: "user", content: userInput }]);
    try {
      await axios.post(
        baseurl +
          `/users/${userID}/${isInnerChat ? "inner_chat_text" : "chat_text"}`,
        {
          text: userInput,
          ...userSettings,
        }
      );
      setInOneChatRound(false);
      setUserInput("");
    } catch (e) {
      message.error("error");
    }
  };

  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        backgroundColor: styles.lightBackground,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Modal
        title="设置"
        open={showSettings}
        footer={null}
        onCancel={() => setShowSettings(false)}
      >
        <Form labelCol={{ span: 4 }} wrapperCol={{ span: 20 }}>
          <Form.Item label="服务器地址">
            <Input
              value={serverAddress}
              onChange={(e) => setServerAddress(e.target.value)}
            />
          </Form.Item>
          <Form.Item label="用户ID">
            <Input value={userID} onChange={(e) => setUserID(e.target.value)} />
          </Form.Item>
          <Form.Item label="其他">
            <Checkbox
              checked={userSettings.reply_in_speech}
              onChange={(e) =>
                setUserSettings((old) => ({
                  ...old,
                  reply_in_speech: e.target.checked,
                }))
              }
            >
              语音回复
            </Checkbox>
            <Checkbox
              checked={userSettings.enable_instruct}
              onChange={(e) =>
                setUserSettings((old) => ({
                  ...old,
                  enable_instruct: e.target.checked,
                }))
              }
            >
              指令模式
            </Checkbox>
            <Checkbox
              checked={userSettings.enable_comment}
              onChange={(e) =>
                setUserSettings((old) => ({
                  ...old,
                  enable_comment: e.target.checked,
                }))
              }
            >
              评论模式
            </Checkbox>
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title="Sign Up"
        open={showSignupModal}
        footer={null}
        onCancel={() => setShowSignupModal(false)}
        centered
      >
        <Form
          name="login"
          onFinish={async (values: any) => {
            await axios.post(baseurl + "/accounts/sign-up", {
              user_id: values.username,
              password: values.password,
            });
            setShowSignupModal(false);
            setUserID(values.username);
          }}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "Please input your Username!" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Username" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please input your Password!" }]}
          >
            <Input
              prefix={<LockOutlined />}
              type="password"
              placeholder="Password"
            />
          </Form.Item>
          <Form.Item>
            <Button block type="primary" htmlType="submit">
              Sign Up
            </Button>
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title="Log In"
        open={showLoginModal}
        footer={null}
        onCancel={() => setShowLoginModal(false)}
        centered
      >
        <Form
          name="login"
          onFinish={async (values: any) => {
            console.log("Received values of form: ", values);
            setShowLoginModal(false);
            await axios.post(baseurl + "/accounts/log-in", {
              user_id: values.username,
              password: values.password,
            });
            setShowSignupModal(false);
            setUserID(values.username);
          }}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "Please input your Username!" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Username" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please input your Password!" }]}
          >
            <Input
              prefix={<LockOutlined />}
              type="password"
              placeholder="Password"
            />
          </Form.Item>
          <Form.Item>
            <Button block type="primary" htmlType="submit">
              Log in
            </Button>
          </Form.Item>
        </Form>
      </Modal>
      <div
        style={{
          height: "50px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 20px",
          backgroundColor: styles.darkBackground,
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center" }}>
          <img
            src="/icon.jpg"
            style={{ width: "16px", height: "16px", marginRight: "20px" }}
          />
          服务器地址：{serverAddress}，用户：{userID}
        </div>
        <div style={{ display: "flex", gap: "16px" }}>
          <Button
            type="default"
            style={{
              backgroundColor: "#bbbddf",
            }}
            shape="round"
            onClick={() => setShowSignupModal(true)}
          >
            Sign Up
          </Button>
          <Button
            type="default"
            style={{
              backgroundColor: "#9ed2f2",
            }}
            shape="round"
            onClick={() => setShowLoginModal(true)}
          >
            Log In
          </Button>

          <Tooltip title="设置">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => setShowSettings(true)}
            />
          </Tooltip>
        </div>
      </div>
      <div
        style={{
          height: "calc(100% - 50px)",
          display: "flex",
          padding: "20px",
          paddingTop: "40px",
          backgroundColor: styles.lightBackground,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: "calc(50% - 20px)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              height: "50px",
              backgroundColor: styles.middleDarkBackground,
              borderRadius: "20px 20px 0px 0px",
              display: "flex",
              alignItems: "center",
              justifyContent: "end",
              padding: "0 20px",
              flexShrink: 0,
            }}
          >
            <Button
              type="primary"
              shape="round"
              onClick={() =>
                axios
                  .post(baseurl + `/users/${userID}/clear_history`)
                  .then(() => setChatMessages([]))
              }
              style={{ backgroundColor: styles.darkDarkBackground }}
            >
              Clear
            </Button>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "20px",
              padding: "20px",
              overflowY: "auto",
              flexGrow: 1,
              backgroundColor: styles.middleBackground,
              borderRadius: "20px",
              marginBottom: "20px",
            }}
          >
            {chatMessages.map((message, index) => {
              const isUser = message.role === "user";
              const extraInfoMarkdown = message.extraInfo
                ? "\n> " + message.extraInfo
                : "";
              return (
                <div
                  key={index}
                  style={{
                    display: "flex",
                    justifyContent: isUser ? "end" : "start",
                  }}
                >
                  <div
                    style={{
                      backgroundColor: isUser
                        ? styles.userTextBackground
                        : styles.systemTextBackground,
                      padding: "0px 20px",
                      borderRadius: "16px",
                      display: isUser ? "flex" : undefined,
                      justifyContent: isUser ? "end" : "start",
                      width: "fit-content",
                      maxWidth: "60%",
                    }}
                  >
                    <Markdown>{`${message.content}${extraInfoMarkdown}`}</Markdown>
                    <div
                      style={{
                        display: "flex",
                        marginBottom: "20px",
                        flexDirection: "column",
                        gap: "10px",
                      }}
                    >
                      {message.files &&
                        message.files.map((filepath, i) => {
                          const fileName = filepath.split(/[\\\/]/).pop();
                          return (
                            <div key={i} style={{ display: "flex", gap: "20px" }}>
                              <Button
                                icon={<FilePdfFilled />}
                                onClick={() =>
                                  setShowPDFURL(
                                    `${baseurl}/users/${userID}/files/${encodeURIComponent(
                                      filepath
                                    )}`
                                  )
                                }
                                style={{ flexShrink: 0 }}
                              />
                              <div>{fileName}</div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div
            style={{
              flexShrink: "0",
              background: styles.darkBackground,
              borderRadius: "20px",
            }}
          >
            <Spin spinning={inOneChatRound && !isInnerChat}>
              <div style={{ padding: "0 20px", paddingTop: "20px" }}>
                <Input.TextArea
                  value={userInput}
                  rows={2}
                  style={{
                    background: "transparent",
                    fontSize: styles.fontSize,
                    border: "none",
                    resize: "none",
                    padding: "0",
                  }}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={async (e) => {
                    if (e.key === "Enter" && !e.shiftKey && userInput !== "") {
                      e.preventDefault();
                      sendUserInput();
                    }
                  }}
                />
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "end",
                  paddingBottom: "10px",
                  paddingRight: "20px",
                }}
              >
                <Button
                  type="primary"
                  shape="round"
                  style={{
                    padding: "4px 20px",
                    backgroundColor: styles.darkDarkBackground,
                  }}
                  onClick={() => sendUserInput()}
                >
                  Send
                </Button>
              </div>
            </Spin>
          </div>
        </div>
        <div
          style={{
            height: "100%",
            width: "50%",
            display: "flex",
            flexDirection: "column",
            backgroundColor: styles.darkBackground,
            borderRadius: "20px",
            marginLeft: "20px",
            flexShrink: 0,
          }}
        >
          <div
            style={{
              height: "50px",
              backgroundColor: styles.middleDarkBackground,
              borderRadius: "20px 20px 0px 0px",
              display: "flex",
              alignItems: "center",
              justifyContent: "end",
              padding: "0 20px",
              flexShrink: 0,
            }}
          >
            <Button
              type="primary"
              shape="round"
              onClick={() => setShowPDFURL(null)}
              style={{ backgroundColor: styles.darkDarkBackground }}
            >
              Close
            </Button>
          </div>
          {showPDFURL ? (
            <div
              style={{
                height: "calc（100% - 50px)",
              }}
            >
              <embed
                src={showPDFURL}
                type="application/pdf"
                width="100%"
                height="100%"
                title="Embedded PDF Viewer"
                style={{ borderRadius: "0 0 20px 20px" }}
              ></embed>
            </div>
          ) : (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "calc(100% - 50px)",
                fontSize: "48px",
                color: "#AAAAAA",
              }}
            >
              暂时没有参考文件
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
