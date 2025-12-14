"use client";

import { useState } from "react";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { useAuth } from "./AuthProvider";

type LoginDialogProps = {
  onLoggedIn?: (token: string) => void;
  triggerVariant?: "primary" | "ghost";
  triggerClassName?: string;
  label?: string;
};

export default function LoginDialog({
  onLoggedIn,
  triggerVariant = "ghost",
  triggerClassName,
  label = "Sign in",
}: LoginDialogProps) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"login" | "signup">("login");
  const { refresh } = useAuth();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant} className={triggerClassName}>
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{tab === "login" ? "Welcome back" : "Create your account"}</DialogTitle>
          <DialogDescription>
            {tab === "login" ? "Sign in to continue searching and save vehicles." : "Start searching with your new account."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2 mb-4">
          <Button variant={tab === "login" ? "primary" : "ghost"} onClick={() => setTab("login")} className="flex-1">
            Sign in
          </Button>
          <Button variant={tab === "signup" ? "primary" : "ghost"} onClick={() => setTab("signup")} className="flex-1">
            Create account
          </Button>
        </div>
        {tab === "login" ? (
          <LoginForm
            onSuccess={(token) => {
              onLoggedIn?.(token);
              void refresh();
              setOpen(false);
            }}
          />
        ) : (
          <SignupForm
            onSuccess={(token) => {
              onLoggedIn?.(token);
              void refresh();
              setOpen(false);
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
