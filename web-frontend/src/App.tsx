import React, { useState } from "react";
import logo from "./logo.svg";
import "./App.css";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Input,
  Card,
  Spin,
  Layout,
  Menu,
  MenuItemProps,
  Button,
  Select,
} from "antd";
import axios from "axios";
import type { MenuItemType } from "antd/es/menu/interface";
import Markdown from "react-markdown";

const baseurl = "http://localhost:8000";

const styles = {
  lightBackground: "#F7F7F7",
  middleBackground: "#F3F3F3",
  darkBackground: "#DEDEDE",
  systemTextBackground: "#FFFFFF",
  userTextBackground: "#A9EA7A",
  fontSize: "24px",
};

const chat_history_example = [
  {
    role: "user",
    content:
      "You are chatting with a user one-to-one\nUser id: realzhao\nMessage: User: hello\n",
    additional_kwargs: {
      date: "2024-08-14",
      time: "21:38:25",
    },
  },
  {
    role: "assistant",
    content: "Hello realzhao! How can I assist you today?",
    additional_kwargs: {
      date: "2024-08-14",
      time: "21:38:28",
    },
  },
];

type ChatHistoryType = typeof chat_history_example;

function ChatHistory() {
  const { isPending, isError, data } = useQuery({
    queryKey: ["chat_history"],
    queryFn: () => axios.get(baseurl + "/chat_history"),
  });

  if (isPending) {
    return <div>loading</div>;
  }

  const history: ChatHistoryType = data?.data;
  if (isError || !history) {
    return <div>error</div>;
  }

  return (
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
      {history.map((msg, index) => {
        const isUser = msg.role === "user";
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
                padding: "10px 20px",
                borderRadius: "4px",
                display: isUser ? "flex" : undefined,
                justifyContent: isUser ? "end" : "start",
                width: "fit-content",
              }}
            >
              {isUser ? (
                msg.content.split("Message: User: ")[1]
              ) : (
                <Markdown>{msg.content}</Markdown>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChatInput() {
  const [userInput, setUserInput] = useState("");
  const queryClient = useQueryClient();

  const mutationUserInput = useMutation({
    mutationFn: (userInput: string) =>
      axios.post(baseurl + "/user_input", { text: userInput }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_history"] });
    },
  });

  const sendUserInput = (userInput: string) => {
    mutationUserInput.mutate(userInput);
    setUserInput("");
  };
  return (
    <div style={{ flexShrink: "0" }}>
      <Spin spinning={mutationUserInput.isPending}>
        <Input.TextArea
          value={userInput}
          rows={8}
          style={{
            background: styles.middleBackground,
            fontSize: styles.fontSize,
            borderRadius: "0",
          }}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && userInput !== "") {
              sendUserInput(userInput);
              e.preventDefault();
            }
          }}
        />
      </Spin>
    </div>
  );
}

function App() {
  const { Header, Content, Footer, Sider } = Layout;
  const [chatSessions, setChatSessions] = useState<string[]>([
    "unnamed session",
  ]);
  const [selectedChatSessionIndex, setSelectedChatSessionIndex] = useState(0);
  return (
    <div style={{ minHeight: "100vh", display: "flex" }}>
      <div
        style={{ minWidth: "300px", backgroundColor: styles.lightBackground }}
      >
        <div
          style={{
            padding: "10px 20px",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <Select
            defaultValue="jack"
            options={[
              { value: "jack", label: "zhaohang" },
              { value: "lucy", label: "zaizheng" },
              { value: "Yiminghe", label: "yichen" },
            ]}
          />
          <Button style={{ padding: "4px 20px" }}>新会话</Button>
        </div>
        {chatSessions.map((session, sessionIndex) => (
          <div
            style={{
              padding: "20px",
              backgroundColor:
                selectedChatSessionIndex === sessionIndex
                  ? styles.darkBackground
                  : undefined,
            }}
          >
            {session}
          </div>
        ))}
      </div>
      <div
        style={{
          backgroundColor: styles.middleBackground,
          height: "100vh",
          display: "flex",
          flexDirection: "column",
          fontSize: styles.fontSize,
          flexGrow: "1",
        }}
      >
        <ChatHistory />
        <ChatInput />
      </div>
    </div>
  );
}

export default App;
