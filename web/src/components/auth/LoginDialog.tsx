"use client";

import { useState } from "react";
import LoginForm from "./LoginForm";
import { Button } from "../ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";

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

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant} className={triggerClassName}>
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Welcome back</DialogTitle>
          <DialogDescription>Sign in to continue searching and save vehicles.</DialogDescription>
        </DialogHeader>
        <LoginForm
          onSuccess={(token) => {
            onLoggedIn?.(token);
            setOpen(false);
          }}
        />
      </DialogContent>
    </Dialog>
  );
}
