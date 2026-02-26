import React from "react";

interface Props {
  title: string;
}

export function ReactComponent({ title }: Props) {
  return <div className="component">{title}</div>;
}
