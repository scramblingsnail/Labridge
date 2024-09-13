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
} from "antd";

import {
  SettingOutlined,
  DeleteOutlined,
  FilePdfFilled,
} from "@ant-design/icons";

const styles = {
  lightBackground: "#F7F7F7",
  middleBackground: "#F3F3F3",
  darkBackground: "#DEDEDE",
  systemTextBackground: "#FFFFFF",
  userTextBackground: "#A9EA7A",
  fontSize: "18px",
};

function App() {
  const [serverAddress, setServerAddress] = useState("localhost:6006");
  const baseurl = "http://" + serverAddress;
  const [userID, setUserID] = useState("realzhao");
  const [userInput, setUserInput] = useState("");
  const [inOneChatRound, setInOneChatRound] = useState(false);
  const [userSettings, setUserSettings] = useState({
    reply_in_speech: false,
    enable_instruct: false,
    enable_comment: false,
  });
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

  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        backgroundColor: styles.lightBackground,
        display: "flex",
        flexDirection: "column",
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
      <div
        style={{
          height: "40px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 20px",
          backgroundColor: styles.darkBackground,
          flexShrink: 0,
        }}
      >
        <div>
          服务器地址：{serverAddress}，用户：{userID}
        </div>
        <div>
          <Tooltip title="重置对话">
            <Button
              type="text"
              icon={<DeleteOutlined />}
              onClick={() =>
                axios
                  .post(baseurl + `/users/${userID}/clear_history`)
                  .then(() => setChatMessages([]))
              }
            />
          </Tooltip>
          <Tooltip title="设置">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => setShowSettings(true)}
            />
          </Tooltip>
        </div>
      </div>
      <div style={{ height: "calc(100% - 40px)", display: "flex" }}>
        <div
          style={{
            height: "100%",
            flexGrow: 1,
            display: "flex",
            flexDirection: "column",
            borderRight: "solid 1px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "20px",
              padding: "20px",
              flexGrow: "1",
              overflowY: "auto",
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
                      borderRadius: "4px",
                      display: isUser ? "flex" : undefined,
                      justifyContent: isUser ? "end" : "start",
                      width: "fit-content",
                      maxWidth: "60%",
                    }}
                  >
                    <Markdown>{`${message.content}${extraInfoMarkdown}`}</Markdown>
                    {message.files &&
                      message.files.map((filepath, _i) => (
                        <div>
                          <Button
                            icon={<FilePdfFilled />}
                            onClick={() =>
                              setShowPDFURL(
                                `${baseurl}/users/${userID}/files/${encodeURIComponent(
                                  filepath
                                )}`
                              )
                            }
                          />
                        </div>
                      ))}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ flexShrink: "0" }}>
            <Spin spinning={inOneChatRound && !isInnerChat}>
              <Input.TextArea
                value={userInput}
                rows={4}
                style={{
                  background: styles.middleBackground,
                  fontSize: styles.fontSize,
                  borderRadius: "0",
                  border: "none",
                  resize: "none",
                  borderTop: "solid 0.5px",
                }}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={async (e) => {
                  if (e.key === "Enter" && !e.shiftKey && userInput !== "") {
                    e.preventDefault();
                    setInOneChatRound(true);
                    setChatMessages([
                      ...chatMessages,
                      { role: "user", content: userInput },
                    ]);
                    try {
                      await axios.post(
                        baseurl +
                          `/users/${userID}/${
                            isInnerChat ? "inner_chat_text" : "chat_text"
                          }`,
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
                  }
                }}
              />
              <div
                style={{
                  display: "flex",
                  justifyContent: "end",
                  backgroundColor: styles.middleBackground,
                  padding: "4px",
                }}
              >
                <Button type="primary">发送</Button>
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
            flexShrink: 0,
          }}
        >
          {showPDFURL ? (
            <embed
              src={showPDFURL}
              type="application/pdf"
              width="100%"
              height="600px"
              title="Embedded PDF Viewer"
            ></embed>
          ) : (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "100%",
                fontSize: "48px",
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
