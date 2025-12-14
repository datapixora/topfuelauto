import TopNav from "../../components/TopNav";
import LoginForm from "../../components/auth/LoginForm";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";

export default function LoginPage() {
  return (
    <div className="space-y-10">
      <TopNav />
      <div className="flex justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-xl">Sign in</CardTitle>
          </CardHeader>
          <CardContent>
            <LoginForm />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
